import mysql.connector
from mysql.connector import Error

class MySQLManager:
    def __init__(self, host="localhost", user="root", password="JOJOJOJO88", database="ia_alice"):
        try:
            self.conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
            self.cursor = self.conn.cursor()
            print("[MySQL] Connexion réussie.")
        except Error as e:
            self.conn = None
            self.cursor = None
            print(f"[MySQL] Erreur de connexion : {e}")

    def save_memory(self, prompt, response):
        if not self.conn or not self.cursor:
            print("[MySQL] Connexion MySQL non établie.")
            return

        try:
            sql = "INSERT INTO memory (prompt, response) VALUES (%s, %s)"
            self.cursor.execute(sql, (prompt, response))
            self.conn.commit()
            print("[MySQL] Mémoire enregistrée.")
        except Error as e:
            print(f"[MySQL] Erreur d'insertion : {e}")

    def fetch_memory(self, limit=100):
        if not self.conn or not self.cursor:
            print("[MySQL] Connexion MySQL non établie.")
            return []

        try:
            self.cursor.execute("SELECT prompt, response FROM memory ORDER BY id DESC LIMIT %s", (limit,))
            return self.cursor.fetchall()
        except Error as e:
            print(f"[MySQL] Erreur de lecture : {e}")
            return []

    def fetch_last_memories(self, limit=5):
        """Récupère les dernières interactions pour le contexte mémoire."""
        return self.fetch_memory(limit)

    def close(self):
        if self.conn and self.conn.is_connected():
            self.cursor.close()
            self.conn.close()
            print("[MySQL] Connexion fermée.")
