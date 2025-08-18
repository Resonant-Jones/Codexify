import logging

for name in ["faiss", "faiss.loader"]:
    logging.getLogger(name).setLevel(logging.ERROR)
    
from guardian.guardian_main import app
if __name__ == "__main__":
    app()