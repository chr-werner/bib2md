import glob
import yaml
import subprocess
import frontmatter
import os
import argparse


def biblatex_to_yaml(input_file: str, output_file: str):
    """Convert a BibLaTeX file to YAML using pybtex-convert.

    Args:
        input_file: Path to the source .bib file.
        output_file: Path where the converted YAML file will be written.

    Raises:
        FileNotFoundError: If the input file does not exist.
        subprocess.CalledProcessError: If pybtex-convert returns a non-zero exit code.
    """
    print("Converting BibLaTeX to YAML...")
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file '{input_file}' not found.")

    try:
        output = subprocess.check_output(
            ["pybtex-convert", input_file, output_file],
            stderr=subprocess.STDOUT,
        )
        print("Conversion completed successfully.")
        if output:
            print("Output:", output.decode())
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to convert BibLaTeX to YAML. {e}")
        raise


def remove_curly_braces(data):
    """Recursively remove all curly brace characters from string values in a data structure.

    Args:
        data: A dict, list, or str to clean. Dicts and lists are traversed recursively.

    Returns:
        The cleaned data with all '{' and '}' characters removed from strings.
    """
    if isinstance(data, dict):
        return {k: remove_curly_braces(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [remove_curly_braces(item) for item in data]
    elif isinstance(data, str):
        return data.replace("{", "").replace("}", "")
    return data


def clean_yaml(input_file: str):
    """Clean and normalise a pybtex-generated YAML file in place.

    Performs the following transformations on each bibliography entry:
    - Removes unwanted keys: comment, file, readstatus, priority, type.
    - Converts 'author' list to 'authors' with Obsidian wiki-link format.
    - Converts 'groups' string to a 'tags' list (splits on comma, strips spaces).
    - Converts 'keywords' string to a list (splits on comma, strips spaces).
    - Strips all curly brace characters from all string values.

    Args:
        input_file: Path to the YAML file to clean. The file is modified in place.
    """
    print("Cleaning YAML data...")
    with open(input_file, "r") as file:
        data = yaml.safe_load(file)

    try:
        for entry in data["entries"]:
            entry_dict = data["entries"][entry]

            # Remove unwanted keys
            for key in ("comment", "file", "readstatus", "priority", "type"):
                entry_dict.pop(key, None)

            # Rename 'author' → 'authors' and format as Obsidian wiki-links
            if "author" in entry_dict:
                authors_list = []
                for author in entry_dict.pop("author"):
                    if "first" in author and "last" in author:
                        full_name = f"[[{author['first']} {author['last']}]]"
                    elif "last" in author:
                        full_name = f"[[{author['last']}]]"
                    else:
                        full_name = ""
                    authors_list.append(full_name)
                entry_dict["authors"] = authors_list

            # Convert 'groups' string → 'tags' list
            if "groups" in entry_dict:
                entry_dict["tags"] = [
                    t.strip() for t in entry_dict.pop("groups").split(",")
                ]

            # Convert 'keywords' string → list
            if "keywords" in entry_dict:
                entry_dict["keywords"] = [
                    k.strip() for k in entry_dict.pop("keywords").split(",")
                ]

        data = remove_curly_braces(data)

        with open(input_file, "w") as file:
            yaml.dump(data, file, default_flow_style=False, allow_unicode=True)

    except Exception as e:
        print(f"Error while cleaning YAML: {e}")
        raise


def update_md(md_file: str, yaml_data: dict):
    """Merge bibliography metadata from yaml_data into a Markdown file's frontmatter.

    For keys whose existing value is a list, unique entries from yaml_data are
    appended. All other keys are created or overwritten.

    Args:
        md_file: Path to the Markdown file to update.
        yaml_data: Dict of metadata fields to merge into the file's frontmatter.
    """
    with open(md_file, "r") as file:
        content = file.read()
    try:
        post = frontmatter.loads(content)

        for key, value in yaml_data.items():
            if key in post.metadata and isinstance(post.metadata[key], list):
                for entry in value:
                    if entry not in post.metadata[key]:
                        post.metadata[key].append(entry)
            else:
                post.metadata[key] = value

        updated_content = frontmatter.dumps(post)
        with open(md_file, "w") as file:
            file.write(updated_content)
    except Exception as e:
        print(f"Failed to parse {md_file}: {e}")


def find_md_files(directory: str) -> list[str]:
    """Recursively find all Markdown files under a directory.

    Args:
        directory: Root directory to search.

    Returns:
        List of absolute paths to all .md files found.
    """
    return glob.glob(os.path.join(directory, "**", "*.md"), recursive=True)


def update(md_files: list[str], yaml_data: dict):
    """Update each Markdown file with its corresponding bibliography entry.

    The entry key is derived from the filename by stripping a leading '@' and
    lowercasing. Files with no matching entry in yaml_data are skipped with a
    warning.

    Args:
        md_files: List of paths to Markdown files.
        yaml_data: Parsed YAML dict containing a top-level 'entries' mapping.
    """
    for file in md_files:
        file_name = os.path.splitext(os.path.basename(file))[0]
        name = file_name.lstrip("@").lower()

        if name not in yaml_data["entries"]:
            print(f"Warning: no BibTeX entry found for '{name}', skipping {file}")
            continue

        update_md(file, yaml_data["entries"][name])


def remove_file(file_path: str):
    """Delete a file if it exists.

    Args:
        file_path: Path to the file to remove.
    """
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Removed temporary file: {file_path}")
    else:
        print(f"File not found, nothing to remove: {file_path}")


def main(bib_file_path: str, yaml_file_path: str, md_path: str):
    """Orchestrate the full BibLaTeX → Markdown frontmatter pipeline.

    1. Converts the .bib file to YAML via pybtex-convert.
    2. Cleans and normalises the YAML.
    3. Finds all Markdown files under md_path and updates their frontmatter.
    4. Removes the temporary YAML file.

    Args:
        bib_file_path: Path to the source BibLaTeX (.bib) file.
        yaml_file_path: Path for the intermediate YAML file.
        md_path: Directory tree containing the Markdown files to update.
    """
    biblatex_to_yaml(bib_file_path, yaml_file_path)
    clean_yaml(yaml_file_path)

    with open(yaml_file_path, "r") as file:
        yaml_data = yaml.safe_load(file)

    md_files = find_md_files(md_path)
    update(md_files, yaml_data)

    remove_file(yaml_file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert BibLaTeX to YAML and update Markdown files."
    )
    parser.add_argument("bib_file_path", help="Path to the BibLaTeX file")
    parser.add_argument(
        "yaml_file_path", help="Path where the YAML output file will be saved"
    )
    parser.add_argument(
        "md_path", help="Path to the directory containing Markdown files"
    )
    args = parser.parse_args()
    main(args.bib_file_path, args.yaml_file_path, args.md_path)
