import os


def is_folder_and_files(folder_path: str, file_list: str):
    """
    Test if a folder and specified files in that folder exist.

    :param folder_path: The path to the folder to check.
    :param file_list: A list of filenames (strings) to check for within the folder.
    :return: A tuple (folder_exists, files_exist) where folder_exists is a boolean indicating
             if the folder exists, and files_exist is a list of booleans indicating if each file exists.
    """
    # Check if the folder exists
    folder_exists = os.path.isdir(folder_path)
    # Check if each file in the list exists within the folder
    files_exist = [
        os.path.isfile(os.path.join(folder_path, file_name)) for file_name in file_list
    ]

    return folder_exists, files_exist
