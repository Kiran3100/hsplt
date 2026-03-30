import os
from pathlib import Path

def combine_files_with_path(project_root, output_file="combined_with_path.txt"):
    project_root = Path(project_root).resolve()
    if not project_root.is_dir():
        print("❌ Given path is not a valid folder.")
        return

    result_lines = []

    # Walk through all files in the folder (including subfolders)
    for file_path in project_root.rglob("*"):
        if file_path.is_file():
            rel_path = file_path.relative_to(project_root)

            # Add header line: the file path
            result_lines.append(f"{'-'*80}")
            result_lines.append(f"FILE: {rel_path}")
            result_lines.append(f"{'-'*80}")

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                result_lines.append(content)
            except Exception as e:
                result_lines.append(f"[ERROR reading file: {e}]")

            result_lines.append("")  # empty line after each file

    # Write everything to the output text file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(result_lines))

    print(f"✅ Done. Combined files into: {Path(output_file).absolute()}")

# Usage
if __name__ == "__main__":
    project_path = input("Enter project folder path: ",).strip()
    combine_files_with_path("D:\LEVITICA\backup\hospital_backend\app")
