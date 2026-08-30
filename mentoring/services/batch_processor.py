import os

class BatchProcessor:
    def __init__(self, inbox_folder: str, archive_folder: str):
        self.inbox = inbox_folder
        self.archive = archive_folder
        os.makedirs(self.inbox, exist_ok=True)
        os.makedirs(self.archive, exist_ok=True)

    def fetch_unprocessed_files(self):
        """
        Returns a list of dicts with file names and contents.
        """
        files = []
        for filename in os.listdir(self.inbox):
            if filename.endswith(".txt") or filename.endswith(".md"):
                filepath = os.path.join(self.inbox, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        text = f.read()
                    files.append({
                        "msg_id": filename,
                        "subject": f"Local File: {filename}",
                        "text": text,
                        "filepath": filepath
                    })
                except Exception as e:
                    print(f"Could not read {filename}: {e}")
        return files

    def archive_file(self, filepath: str):
        """
        Moves a processed file to the archive folder.
        """
        filename = os.path.basename(filepath)
        archive_path = os.path.join(self.archive, filename)
        try:
            os.rename(filepath, archive_path)
            print(f"Archived {filename}")
        except Exception as e:
            print(f"Could not archive {filename}: {e}")
