from app import db, Setting

# Force update active status to True on all settings
with db.engine.connect() as connection:
    connection.execute("UPDATE setting SET active_status = 1")
    print("Updated all settings to active status")
