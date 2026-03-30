import os
import shutil

def clean_python_cache(folder_path):
    if not os.path.exists(folder_path):
        print("❌ Folder path does not exist!")
        return

    deleted_folders = 0
    deleted_files = 0

    for root, dirs, files in os.walk(folder_path):

        # 🔥 Delete __pycache__ folders
        for dir_name in dirs[:]:  # use copy to safely modify
            if dir_name == "__pycache__":
                pycache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(pycache_path)
                    print(f"🗑️ Deleted folder: {pycache_path}")
                    deleted_folders += 1
                    dirs.remove(dir_name)  # prevent re-traversal
                except Exception as e:
                    print(f"❌ Error deleting {pycache_path}: {e}")

        # 🔥 Delete .pyc files
        for file in files:
            if file.endswith(".pyc"):
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    print(f"🗑️ Deleted file: {file_path}")
                    deleted_files += 1
                except Exception as e:
                    print(f"❌ Error deleting {file_path}: {e}")

    print("\n✅ Cleanup completed!")
    print(f"📁 __pycache__ folders deleted: {deleted_folders}")
    print(f"📄 .pyc files deleted: {deleted_files}")


# 👉 Use your project path
folder_path = r"D:\LEVITICA\backup\hospital_backend"

clean_python_cache(folder_path)