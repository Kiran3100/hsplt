import os

def combine_files_to_text(folder_path, output_file):
    if not os.path.exists(folder_path):
        print("❌ Folder path does not exist!")
        return

    # 🚫 Files & folders to ignore
    ignore_folders = {"__pycache__", ".git", ".venv", "venv"}
    ignore_extensions = {".pyc", ".log", ".db", ".sqlite3"}

    with open(output_file, 'w', encoding='utf-8') as outfile:
        
        for root, dirs, files in os.walk(folder_path):

            # 👉 Remove ignored folders from traversal
            dirs[:] = [d for d in dirs if d not in ignore_folders]

            for file in files:
                file_path = os.path.join(root, file)

                # 👉 Skip ignored file types
                if any(file.endswith(ext) for ext in ignore_extensions):
                    continue

                try:
                    # Write marker/header
                    outfile.write("\n" + "="*80 + "\n")
                    outfile.write(f"FILE: {file_path}\n")
                    outfile.write("="*80 + "\n\n")

                    # Read content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                        outfile.write(infile.read())
                        outfile.write("\n\n")

                except Exception as e:
                    outfile.write(f"\nError reading file: {file_path}\n{str(e)}\n")

    print(f"✅ Done! Output saved in: {output_file}")


# 👉 Use your folder path
folder_path = r"D:\LEVITICA\backup\hospital_backend\app\utils"
output_file = "utils.txt"

combine_files_to_text(folder_path, output_file)