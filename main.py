import yaml
import subprocess
import frontmatter
import os


def biblatex_to_yaml(input_file: str, output_file: str):
    print("Converting BibLaTeX to YAML...")
    try:
        # Check if the input file exists
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file '{input_file}' not found.")

        # Run the command and capture its output
        command = f"pybtex-convert {input_file} {output_file}"
        output = subprocess.check_output(command, shell=True)
        print("Conversion completed successfully.")
        print("Output:", output.decode())
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to convert BibLaTeX to YAML. {e}")


def remove_curly_braces(data):
    if isinstance(data, dict):
        # If the data is a dictionary, iterate through its keys and values
        for key, value in data.items():
            # Recursively remove curly braces from the dictionary values
            data[key] = remove_curly_braces(value)
    elif isinstance(data, list):
        # If the data is a list, iterate through its elements
        data = [remove_curly_braces(item) for item in data]
    elif isinstance(data, str):
        # If the data is a string, remove curly braces from the string
        data = data.replace("{", "").replace("}", "")
    # Return the modified data
    return data


def clean_yaml(input_file: str):
    print("Cleaning YAML data...")
    # Read the YAML file
    with open(input_file, "r") as file:
        data = yaml.safe_load(file)

    try:
        # cleaning
        for entry in data["entries"]:
            entry_dict = data["entries"][entry]

            # delete unwanted key value pairs
            if "comment" in entry_dict.keys():
                del entry_dict["comment"]
            if "file" in entry_dict.keys():
                del entry_dict["file"]
            if "readstatus" in entry_dict.keys():
                del entry_dict["readstatus"]
            if "priority" in entry_dict.keys():
                del entry_dict["priority"]
            if "type" in entry_dict.keys():
                del entry_dict["type"]

            # Modify 'author' to 'authors' and concatenate 'first' and 'last' names
            if "author" in entry_dict.keys():
                authors_list = []
                for author in entry_dict.pop("author"):
                    if "first" in author.keys() and "last" in author.keys():
                        full_name = f"[[{author['first']} {author['last']}]]"
                    elif "last" in author.keys():
                        full_name = f"[[{author['last']}]]"
                    else:
                        full_name = ""
                    authors_list.append(full_name)
                entry_dict["authors"] = authors_list

            # convert groups to list of tags
            if "groups" in entry_dict.keys():
                entry_dict["tags"] = (
                    entry_dict.pop("groups").replace(" ", "").split(",")
                )
                
            # convert keywords to list of tags
            if "keywords" in entry_dict.keys():
                entry_dict["keywords"] = (
                    entry_dict.pop("keywords").split(",")
                )

        # Remove all '{' and '}' characters from the values in the entry
        remove_curly_braces(data)

        # Write the modified content back to the file
        with open(input_file, "w") as file:
            yaml.dump(data, file)
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def update_md(md_file: str, yaml_data: dict):
    # Read the Markdown file
    with open(md_file, "r") as file:
        content = file.read()
    try:
        # Parse frontmatter and content
        post = frontmatter.loads(content)

        for key in yaml_data.keys():
            # check if key is already in metadata and if it is a list
            if key in post.metadata and isinstance(post.metadata[key], list):
                # If it's a list, append unique entries from another list
                for entry in yaml_data[key]:
                    if entry not in post.metadata[key]:
                        post.metadata[key].append(entry)
            # else write it as new or overwrite it
            else:
                post.metadata[key] = yaml_data[key]

        # Reconstruct Markdown content with updated properties
        updated_content = frontmatter.dumps(post)
        # Write the updated content back to the file
        with open(md_file, "w") as file:
            file.write(updated_content)
    except:
        print(f"failed to parse {md_file}...")



def find_md_files(directory):
    md_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                md_files.append(os.path.join(root, file))
    return md_files


def update(md_files, yaml_data):
    for file in md_files:
        # get name only
        file_name, file_extension = os.path.splitext(
            os.path.basename(file)
        )  # Split the file name and extension
        name = file_name.lstrip("@").lower()

        print(file)
        update_md(file, yaml_data["entries"][name])

def remove_file(file_path):
    # Check if the file exists before attempting to delete it
    if os.path.exists(file_path):
        # Delete the file
        os.remove(file_path)
        print(f"The file {file_path} has been deleted successfully.")
    else:
        print(f"The file {file_path} does not exist.")


def main():
    # Ask user for input
    bib_file_path = "/home/werchr/HSW/Research/PhD-obsidian/sources.bib"  # input("Enter the path to your BibLaTeX file: ")
    yaml_file_path = "/home/werchr/HSW/Research/PhD-obsidian/sources.yaml"  # input("Enter the path where you want to save the YAML output file: ")
    md_path = "/home/werchr/HSW/Research/PhD-obsidian/sources"

    biblatex_to_yaml(bib_file_path, yaml_file_path)
    clean_yaml(yaml_file_path)

    with open(yaml_file_path, "r") as file:
        yaml_data = yaml.safe_load(file)

    md_files = find_md_files(md_path)

    update(md_files, yaml_data)
    remove_file(yaml_file_path)

if __name__ == "__main__":
    main()
