from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask_socketio import SocketIO
import os

# ============================================================
# Initialisation de l'application Flask
# ============================================================
# Je crée ici l'application principale Flask qui va gérer
# l'ensemble du site web d'astronomie.
app = Flask(__name__)

# SocketIO me sert pour la partie "Actualités" en temps réel.
# Cela permet de mettre à jour la page sans rechargement complet.
socketio = SocketIO(app)

# Clé secrète utilisée par Flask pour sécuriser les sessions
# utilisateur et les messages flash.
app.secret_key = "astro-secret-key-2026"

# ============================================================
# Configuration de la base de données MySQL / MariaDB
# ============================================================
# J'utilise ici Flask-SQLAlchemy pour me connecter à la base
# "astronomie" avec l'utilisateur "astro".
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://astro:astro123@localhost/astronomie"

# Cette option est désactivée pour éviter des surcoûts inutiles
# de suivi des modifications des objets SQLAlchemy.
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialisation de l'objet SQLAlchemy.
db = SQLAlchemy(app)


# ============================================================
# Modèle User
# ============================================================
# Cette table stocke les utilisateurs du site.
# Chaque utilisateur possède un identifiant, un nom d'utilisateur
# unique et un mot de passe hashé.
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"


# ============================================================
# Modèle Camera
# ============================================================
# Cette table contient les appareils photo affichés dans le site.
# J'ai prévu une catégorie, une marque, un modèle, une date
# de sortie, un score, ainsi qu'un résumé pour la partie
# "aller plus loin".
class Camera(db.Model):
    __tablename__ = "cameras"

    id = db.Column(db.Integer, primary_key=True)
    categorie = db.Column(db.String(100), nullable=False)
    marque = db.Column(db.String(100), nullable=False)
    modele = db.Column(db.String(100), nullable=False)
    date_sortie = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    resume = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Camera {self.marque} {self.modele}>"


# ============================================================
# Modèle Telescope
# ============================================================
# Cette table contient les télescopes du site.
# Même logique que pour les appareils photo :
# catégorie, marque, modèle, date, score et résumé.
class Telescope(db.Model):
    __tablename__ = "telescopes"

    id = db.Column(db.Integer, primary_key=True)
    categorie = db.Column(db.String(100), nullable=False)
    marque = db.Column(db.String(100), nullable=False)
    modele = db.Column(db.String(100), nullable=False)
    date_sortie = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    resume = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Telescope {self.marque} {self.modele}>"


# ============================================================
# Modèle News
# ============================================================
# Cette table stocke les actualités du site.
# Elle est utilisée pour la page "Actualités" et pour la
# mise à jour temps réel via SocketIO.
class News(db.Model):
    __tablename__ = "news"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    date_publication = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"<News {self.titre}>"


# ============================================================
# Décorateur de protection des routes
# ============================================================
# Cette fonction me permet de protéger facilement les pages
# du site. Si l'utilisateur n'est pas connecté, il est
# redirigé automatiquement vers la page de connexion.
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# Route d'accueil
# ============================================================
# Quand on arrive sur "/", je redirige directement vers la
# page de connexion.
@app.route("/")
def index():
    return redirect(url_for("login"))


# ============================================================
# Inscription
# ============================================================
# Cette route gère à la fois l'affichage du formulaire
# d'inscription (GET) et le traitement du formulaire (POST).
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Je récupère les champs saisis par l'utilisateur.
        username = request.form["username"].strip()
        password = request.form["password"]

        # Vérification simple : aucun champ ne doit être vide.
        if not username or not password:
            flash("Veuillez remplir tous les champs.", "danger")
            return redirect(url_for("register"))

        # Je vérifie que le nom d'utilisateur n'existe pas déjà.
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Ce nom d'utilisateur existe déjà.", "danger")
            return redirect(url_for("register"))

        # Le mot de passe est hashé avant d'être stocké en base.
        hashed_password = generate_password_hash(password)

        # Création puis sauvegarde du nouvel utilisateur.
        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Inscription réussie. Vous pouvez maintenant vous connecter.", "success")
        return redirect(url_for("login"))

    # Si la méthode est GET, j'affiche simplement le formulaire.
    return render_template("register.html")


# ============================================================
# Connexion
# ============================================================
# Cette route gère l'affichage du formulaire de connexion
# et la vérification des identifiants.
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        # Recherche de l'utilisateur à partir du username.
        user = User.query.filter_by(username=username).first()

        # Si l'utilisateur existe et que le mot de passe correspond,
        # je stocke ses informations de session.
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            return redirect(url_for("home"))

        # Sinon, message d'erreur et retour à la page de login.
        flash("Identifiants invalides.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


# ============================================================
# Déconnexion
# ============================================================
# Je vide complètement la session pour déconnecter proprement
# l'utilisateur.
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# Page d'accueil après connexion
# ============================================================
# Cette page n'est accessible qu'à un utilisateur connecté.
@app.route("/home")
@login_required
def home():
    return render_template("home.html")


# ============================================================
# Liste des appareils photo
# ============================================================
# Je récupère ici les appareils photo par catégories afin de
# les afficher séparément dans la page cameras.html.
@app.route("/cameras")
@login_required
def cameras():
    cameras_amateur = Camera.query.filter_by(categorie="Amateur").all()
    cameras_serieux = Camera.query.filter_by(categorie="Amateur sérieux").all()
    cameras_pro = Camera.query.filter_by(categorie="Professionnel").all()

    return render_template(
        "cameras.html",
        cameras_amateur=cameras_amateur,
        cameras_serieux=cameras_serieux,
        cameras_pro=cameras_pro
    )


# ============================================================
# Fonction utilitaire : associer une caméra à son image
# ============================================================
# Cette fonction me permet de faire le lien entre un objet
# Camera en base et le nom du fichier image stocké dans
# static/images/photographies.
def get_camera_image_filename(camera):
    images = {
        ("Canon", "EOS 2000D"): "Canon_EOS2000D.png",
        ("Nikon", "D3500"): "Nikon_D3500.png",
        ("Sony", "Alpha 6400"): "Sony_Alpha 6400.png",
        ("Canon", "EOS 90D"): "Canon_EOS90D.png",
        ("Sony", "Alpha 7 IV"): "Sony_Alpha7IV.png",
        ("Canon", "EOS R5"): "Canon_EOSR5.png",
    }

    # Si aucune image précise n'est trouvée, j'utilise
    # une image générique.
    return images.get((camera.marque, camera.modele), "astronomie-og.jpg")


# ============================================================
# Détail d'un appareil photo
# ============================================================
# Cette page affiche les informations détaillées d'un appareil
# photo ainsi que son image associée.
@app.route("/cameras/<int:camera_id>")
@login_required
def camera_detail(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    image_filename = get_camera_image_filename(camera)
    return render_template("camera_detail.html", camera=camera, image_filename=image_filename)


# ============================================================
# Page Photographies
# ============================================================
# Cette page parcourt automatiquement le dossier contenant
# les images et affiche toutes les photos disponibles.
@app.route("/photographies")
@login_required
def photographies():
    dossier_photos = os.path.join(app.root_path, "static", "images", "photographies")

    # Extensions de fichiers autorisées.
    extensions_valides = (".jpg", ".jpeg", ".png", ".webp")
    photos = []

    # Si le dossier existe, je récupère uniquement les images.
    if os.path.exists(dossier_photos):
        photos = [
            fichier for fichier in os.listdir(dossier_photos)
            if fichier.lower().endswith(extensions_valides)
        ]
        photos.sort()

    return render_template("photographies.html", photos=photos)


# ============================================================
# Liste des télescopes
# ============================================================
# Même logique que pour les appareils photo :
# je sépare les télescopes par catégories pour les afficher
# clairement dans la page telescopes.html.
@app.route("/telescopes")
@login_required
def telescopes():
    telescopes_enfants = Telescope.query.filter_by(categorie="Téléscopes pour enfants").all()
    telescopes_auto = Telescope.query.filter_by(categorie="Automatisés").all()
    telescopes_complets = Telescope.query.filter_by(categorie="Téléscopes complets").all()

    return render_template(
        "telescopes.html",
        telescopes_enfants=telescopes_enfants,
        telescopes_auto=telescopes_auto,
        telescopes_complets=telescopes_complets
    )


# ============================================================
# Fonction utilitaire : associer un télescope à son image
# ============================================================
# Comme pour les appareils photo, je fais ici la correspondance
# entre les données de la base et le bon fichier image.
def get_telescope_image_filename(telescope):
    images = {
        ("Bresser", "Junior 45/600"): "Bresser_Junior45_600.png",
        ("Celestron", "Kids 50TT"): "CelestronKids50TT.png",
        ("Celestron", "NexStar 6SE"): "Celestron_NexStar6SE.jpg",
        ("Sky-Watcher", "Skymax 127 SynScan"): "astronomie-og.jpg",
        ("Meade", "Polaris 130 EQ"): "astronomie-og.jpg",
        ("Sky-Watcher", "Explorer 200P"): "astronomie-og.jpg",
    }

    return images.get((telescope.marque, telescope.modele), "astronomie-og.jpg")


# ============================================================
# Détail d'un télescope
# ============================================================
# Cette page affiche les informations détaillées d'un télescope
# ainsi que l'image qui lui correspond.
@app.route("/telescopes/<int:telescope_id>")
@login_required
def telescope_detail(telescope_id):
    telescope = Telescope.query.get_or_404(telescope_id)
    image_filename = get_telescope_image_filename(telescope)
    return render_template("telescope_detail.html", telescope=telescope, image_filename=image_filename)


# ============================================================
# Liste des actualités
# ============================================================
# Cette page affiche les actualités de la plus récente à la plus
# ancienne.
@app.route("/actualites")
@login_required
def actualites():
    actualites = News.query.order_by(News.id.desc()).all()
    return render_template("actualites.html", actualites=actualites)


# ============================================================
# Ajout d'une actualité
# ============================================================
# Cette route permet d'ajouter une nouvelle actualité via un
# formulaire. Une fois l'actualité enregistrée, j'envoie un
# événement SocketIO pour mettre à jour la page Actualités
# en temps réel.
@app.route("/actualites/add", methods=["GET", "POST"])
@login_required
def add_actualite():
    if request.method == "POST":
        titre = request.form["titre"].strip()
        contenu = request.form["contenu"].strip()
        date_publication = request.form["date_publication"].strip()

        # Vérification simple des champs.
        if not titre or not contenu or not date_publication:
            flash("Veuillez remplir tous les champs.", "danger")
            return redirect(url_for("add_actualite"))

        # Création de la nouvelle actualité.
        nouvelle_actu = News(
            titre=titre,
            contenu=contenu,
            date_publication=date_publication
        )
        db.session.add(nouvelle_actu)
        db.session.commit()

        # Envoi en temps réel aux clients connectés.
        socketio.emit("nouvelle_actualite", {
            "id": nouvelle_actu.id,
            "titre": nouvelle_actu.titre,
            "contenu": nouvelle_actu.contenu,
            "date_publication": nouvelle_actu.date_publication
        })

        flash("Actualité ajoutée avec succès.", "success")
        return redirect(url_for("actualites"))

    return render_template("add_actualite.html")


# ============================================================
# Point d'entrée principal de l'application
# ============================================================
# Je lance ici l'application avec SocketIO pour que les websockets
# fonctionnent correctement, notamment pour les actualités en temps réel.
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)