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

    def save_memory(self, prompt: str, response: str):
        try:
            query = "INSERT INTO memory (prompt, response) VALUES (%s, %s)"
            self.cursor.execute(query, (prompt, response))
            self.conn.commit()
            print("[MySQL] Mémoire sauvegardée.")
        except Exception as e:
            print(f"[ERREUR] [MÉMOIRE] Échec de la sauvegarde en base de données : {str(e)}")

    def fetch_memory(self, limit=100):
        if not self.conn or not self.cursor:
            print("[MySQL] Connexion MySQL non établie.")
            return []

        try:
            self.cursor.execute("SELECT prompt, response FROM memory ORDER BY id DESC LIMIT %s", (limit,))  # Nom de la table "memory"
            return self.cursor.fetchall()
        except Error as e:
            print(f"[MySQL] Erreur de lecture : {e}")
            return []

    def fetch_last_memories(self, limit=5):
        try:
            query = "SELECT prompt, response FROM memory ORDER BY created_at DESC LIMIT %s"  # Nom de la table "memory"
            self.cursor.execute(query, (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"[ERREUR] [MÉMOIRE] Échec de la récupération des mémoires : {str(e)}")
            return []

    def close(self):
        if self.conn and self.conn.is_connected():
            self.cursor.close()
            self.conn.close()
            print("[MySQL] Connexion fermée.")

    def delete_memory_by_id(self, memory_id: int):
        """Supprime une entrée mémoire spécifique par son ID."""
        try:
            query = "DELETE FROM memory WHERE id = %s"  # Nom de la table "memory"
            self.cursor.execute(query, (memory_id,))
            self.conn.commit()
            print(f"[BDD] Mémoire ID {memory_id} supprimée.")
        except Exception as e:
            print(f"[ERREUR] Suppression mémoire ID {memory_id} : {e}")
