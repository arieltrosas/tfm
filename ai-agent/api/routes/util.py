import tkinter as tk
from tkinter import filedialog
from fastapi import APIRouter

router = APIRouter()

@router.get("/util/browse-files", tags=["Dev Utilities"])
def browse_local_files():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    file_paths = filedialog.askopenfilenames(title="Select Files for API Testing")
    
    root.destroy()
    
    return {"file_paths": list(file_paths)}