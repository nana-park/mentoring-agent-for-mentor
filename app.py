"""Compatibility entry point for python app.py and flask --app app."""
from mentoring.web.app import app, main

if __name__ == "__main__":
    main()
