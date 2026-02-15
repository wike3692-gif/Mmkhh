"""A simple command-line TODO list application."""

import json
import os

DATA_FILE = "todos.json"


def load_todos():
    """Load todos from the JSON data file."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_todos(todos):
    """Save todos to the JSON data file."""
    with open(DATA_FILE, "w") as f:
        json.dump(todos, f, indent=2)


def add_todo(title):
    """Add a new todo item."""
    todos = load_todos()
    todo = {
        "id": len(todos) + 1,
        "title": title,
        "done": False,
    }
    todos.append(todo)
    save_todos(todos)
    print(f"Added: {title}")


def list_todos():
    """List all todo items."""
    todos = load_todos()
    if not todos:
        print("No todos yet.")
        return
    for todo in todos:
        status = "x" if todo["done"] else " "
        print(f"[{status}] {todo['id']}. {todo['title']}")


def complete_todo(todo_id):
    """Mark a todo item as complete."""
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["done"] = True
            save_todos(todos)
            print(f"Completed: {todo['title']}")
            return
    print(f"Todo with id {todo_id} not found.")


def delete_todo(todo_id):
    """Delete a todo item by its id."""
    todos = load_todos()
    for i, todo in enumerate(todos):
        if todo["id"] == todo_id:
            removed = todos.pop(i)
            save_todos(todos)
            print(f"Deleted: {removed['title']}")
            return
    print(f"Todo with id {todo_id} not found.")


# TODO: Implement a function to search todos by keyword in the title


# TODO: Add a priority field (low, medium, high) to todo items


# TODO: Implement a function to display summary stats (total, completed, pending)


def main():
    """Main entry point with a simple CLI interface."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python todo_app.py <command> [args]")
        print("Commands: add, list, complete, delete, search, stats")
        return

    command = sys.argv[1]

    if command == "add":
        if len(sys.argv) < 3:
            print("Usage: python todo_app.py add <title>")
            return
        add_todo(" ".join(sys.argv[2:]))
    elif command == "list":
        list_todos()
    elif command == "complete":
        if len(sys.argv) < 3:
            print("Usage: python todo_app.py complete <id>")
            return
        complete_todo(int(sys.argv[2]))
    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python todo_app.py delete <id>")
            return
        delete_todo(int(sys.argv[2]))
    elif command == "search":
        # TODO: Wire up the search command once search_todos is implemented
        print("Search is not yet implemented.")
    elif command == "stats":
        # TODO: Wire up the stats command once show_stats is implemented
        print("Stats is not yet implemented.")
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
