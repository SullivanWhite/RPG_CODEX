import sqlite3

from flask import Flask, abort, flash, redirect, render_template, request, url_for

from database import get_db, init_db


app = Flask(__name__)
app.secret_key = "rpg-codex-development-key"
init_db(app)


def get_campaign():
    return get_db().execute("SELECT * FROM campaigns ORDER BY id LIMIT 1").fetchone()


def optional_int(field):
    value = request.form.get(field, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def get_faction_or_404(faction_id, campaign_id):
    faction = get_db().execute("""
        SELECT * FROM factions WHERE id = ? AND campaign_id = ?
    """, (faction_id, campaign_id)).fetchone()
    if faction is None:
        abort(404)
    return faction


def text_field(name, limit=100):
    value = request.form.get(name, "").strip()
    return value if value and len(value) <= limit else None


@app.route("/")
def dashboard():
    campaign = get_campaign()
    db = get_db()
    location_count = db.execute("SELECT COUNT(*) FROM locations WHERE campaign_id = ?", (campaign["id"],)).fetchone()[0]
    character_count = db.execute("SELECT COUNT(*) FROM characters WHERE campaign_id = ?", (campaign["id"],)).fetchone()[0]
    faction_count = db.execute("SELECT COUNT(*) FROM factions WHERE campaign_id = ?", (campaign["id"],)).fetchone()[0]
    creature_count = db.execute("SELECT COUNT(*) FROM creatures WHERE campaign_id = ?", (campaign["id"],)).fetchone()[0]
    item_count = db.execute("SELECT COUNT(*) FROM items WHERE campaign_id = ?", (campaign["id"],)).fetchone()[0]
    return render_template("dashboard.html", campaign=campaign, location_count=location_count, character_count=character_count, faction_count=faction_count, creature_count=creature_count, item_count=item_count)


@app.route("/locations")
def locations():
    campaign = get_campaign()
    rows = get_db().execute("SELECT * FROM locations WHERE campaign_id = ? ORDER BY name COLLATE NOCASE", (campaign["id"],)).fetchall()
    return render_template("locations/list.html", locations=rows, campaign=campaign)


@app.route("/locations/new", methods=["GET", "POST"])
def location_new():
    campaign = get_campaign()
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("locations/form.html", location=None)
        db.execute("""
            INSERT INTO locations (campaign_id, name, category, summary, description, secret_notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (campaign["id"], name, request.form.get("category", "Otro"), request.form.get("summary", "").strip(), request.form.get("description", "").strip(), request.form.get("secret_notes", "").strip()))
        db.commit()
        flash("Localización creada correctamente.", "success")
        return redirect(url_for("locations"))
    return render_template("locations/form.html", location=None)


@app.route("/locations/<int:location_id>")
def location_detail(location_id):
    campaign = get_campaign()
    db = get_db()
    location = db.execute("SELECT * FROM locations WHERE id = ? AND campaign_id = ?", (location_id, campaign["id"])).fetchone()
    if location is None:
        abort(404)
    factions = db.execute("""
        SELECT factions.*, faction_locations.relationship_type, faction_locations.description AS link_description
        FROM faction_locations JOIN factions ON factions.id = faction_locations.faction_id
        WHERE faction_locations.location_id = ? AND factions.campaign_id = ?
        ORDER BY factions.name COLLATE NOCASE
    """, (location_id, campaign["id"])).fetchall()
    return render_template("locations/detail.html", location=location, factions=factions)


@app.route("/locations/<int:location_id>/edit", methods=["GET", "POST"])
def location_edit(location_id):
    campaign = get_campaign()
    db = get_db()
    location = db.execute("SELECT * FROM locations WHERE id = ? AND campaign_id = ?", (location_id, campaign["id"])).fetchone()
    if location is None:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("locations/form.html", location=location)
        db.execute("""
            UPDATE locations SET name = ?, category = ?, summary = ?, description = ?, secret_notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND campaign_id = ?
        """, (name, request.form.get("category", "Otro"), request.form.get("summary", "").strip(), request.form.get("description", "").strip(), request.form.get("secret_notes", "").strip(), location_id, campaign["id"]))
        db.commit()
        flash("Localización actualizada.", "success")
        return redirect(url_for("location_detail", location_id=location_id))
    return render_template("locations/form.html", location=location)


@app.route("/locations/<int:location_id>/delete", methods=["POST"])
def location_delete(location_id):
    campaign = get_campaign()
    db = get_db()
    db.execute("DELETE FROM locations WHERE id = ? AND campaign_id = ?", (location_id, campaign["id"]))
    db.commit()
    flash("Localización eliminada.", "success")
    return redirect(url_for("locations"))


@app.route("/characters")
def characters():
    campaign = get_campaign()
    rows = get_db().execute("""
        SELECT characters.*, locations.name AS location_name FROM characters
        LEFT JOIN locations ON characters.location_id = locations.id
        WHERE characters.campaign_id = ? ORDER BY characters.name COLLATE NOCASE
    """, (campaign["id"],)).fetchall()
    return render_template("characters/list.html", characters=rows, campaign=campaign)


def character_locations(campaign_id):
    return get_db().execute("SELECT id, name FROM locations WHERE campaign_id = ? ORDER BY name COLLATE NOCASE", (campaign_id,)).fetchall()


def form_location_id(db, campaign_id):
    value = request.form.get("location_id", "").strip()
    location_id = int(value) if value.isdigit() else None
    if location_id is not None:
        valid = db.execute("SELECT id FROM locations WHERE id = ? AND campaign_id = ?", (location_id, campaign_id)).fetchone()
        if valid is None:
            abort(400)
    return location_id


def save_character_values():
    character_type = request.form.get("character_type", "narrative")
    if character_type not in {"narrative", "statblock", "creature", "important"}:
        abort(400)
    return (character_type, request.form.get("ancestry", "").strip(), request.form.get("age", "").strip(), request.form.get("occupation", "").strip(), request.form.get("character_class", "").strip(), optional_int("level"), request.form.get("summary", "").strip(), request.form.get("personality", "").strip(), request.form.get("biography", "").strip(), request.form.get("motivations", "").strip(), optional_int("armor_class"), optional_int("hit_points"), request.form.get("perception", "").strip(), request.form.get("saving_throws", "").strip(), request.form.get("skills", "").strip(), request.form.get("attacks", "").strip(), request.form.get("abilities", "").strip(), request.form.get("portrait_url", "").strip(), request.form.get("secret_notes", "").strip())


@app.route("/characters/new", methods=["GET", "POST"])
def character_new():
    campaign = get_campaign()
    db = get_db()
    locations_for_form = character_locations(campaign["id"])
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("characters/form.html", character=None, locations=locations_for_form)
        values = save_character_values()
        db.execute("""
            INSERT INTO characters (campaign_id, location_id, name, character_type, ancestry, age, occupation, character_class, level, summary, personality, biography, motivations, armor_class, hit_points, perception, saving_throws, skills, attacks, abilities, portrait_url, secret_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (campaign["id"], form_location_id(db, campaign["id"]), name, *values))
        db.commit()
        flash("Personaje creado correctamente.", "success")
        return redirect(url_for("characters"))
    return render_template("characters/form.html", character=None, locations=locations_for_form)


@app.route("/characters/<int:character_id>")
def character_detail(character_id):
    campaign = get_campaign()
    db = get_db()
    character = db.execute("""
        SELECT characters.*, locations.name AS location_name FROM characters
        LEFT JOIN locations ON characters.location_id = locations.id
        WHERE characters.id = ? AND characters.campaign_id = ?
    """, (character_id, campaign["id"])).fetchone()
    if character is None:
        abort(404)
    relationships = db.execute("""
        SELECT character_relationships.*, characters.name AS related_name, characters.id AS related_id, characters.ancestry AS related_ancestry
        FROM character_relationships JOIN characters ON character_relationships.related_character_id = characters.id
        WHERE character_relationships.character_id = ? ORDER BY characters.name COLLATE NOCASE
    """, (character_id,)).fetchall()
    available_characters = db.execute("SELECT id, name FROM characters WHERE campaign_id = ? AND id != ? ORDER BY name COLLATE NOCASE", (campaign["id"], character_id)).fetchall()
    factions = db.execute("""
        SELECT factions.*, faction_memberships.role, faction_memberships.description AS membership_description
        FROM faction_memberships JOIN factions ON factions.id = faction_memberships.faction_id
        WHERE faction_memberships.character_id = ? AND factions.campaign_id = ?
        ORDER BY factions.name COLLATE NOCASE
    """, (character_id, campaign["id"])).fetchall()
    return render_template("characters/detail.html", character=character, relationships=relationships, available_characters=available_characters, factions=factions)


@app.route("/characters/<int:character_id>/edit", methods=["GET", "POST"])
def character_edit(character_id):
    campaign = get_campaign()
    db = get_db()
    character = db.execute("SELECT * FROM characters WHERE id = ? AND campaign_id = ?", (character_id, campaign["id"])).fetchone()
    if character is None:
        abort(404)
    locations_for_form = character_locations(campaign["id"])
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("characters/form.html", character=character, locations=locations_for_form)
        values = save_character_values()
        db.execute("""
            UPDATE characters SET location_id=?, name=?, character_type=?, ancestry=?, age=?, occupation=?, character_class=?, level=?, summary=?, personality=?, biography=?, motivations=?, armor_class=?, hit_points=?, perception=?, saving_throws=?, skills=?, attacks=?, abilities=?, portrait_url=?, secret_notes=?, updated_at=CURRENT_TIMESTAMP
            WHERE id = ? AND campaign_id = ?
        """, (form_location_id(db, campaign["id"]), name, *values, character_id, campaign["id"]))
        db.commit()
        flash("Personaje actualizado.", "success")
        return redirect(url_for("character_detail", character_id=character_id))
    return render_template("characters/form.html", character=character, locations=locations_for_form)


@app.route("/characters/<int:character_id>/delete", methods=["POST"])
def character_delete(character_id):
    campaign = get_campaign()
    db = get_db()
    db.execute("DELETE FROM characters WHERE id = ? AND campaign_id = ?", (character_id, campaign["id"]))
    db.commit()
    flash("Personaje eliminado.", "success")
    return redirect(url_for("characters"))


@app.route("/characters/<int:character_id>/relationships", methods=["POST"])
def relationship_create(character_id):
    campaign = get_campaign()
    db = get_db()
    source = db.execute("SELECT id FROM characters WHERE id = ? AND campaign_id = ?", (character_id, campaign["id"])).fetchone()
    target_value = request.form.get("related_character_id", "").strip()
    relationship_type = text_field("relationship_type")
    if source is None:
        abort(404)
    if not target_value.isdigit() or relationship_type is None:
        flash("Indica un personaje y un tipo de relación válido.", "error")
        return redirect(url_for("character_detail", character_id=character_id))
    target_id = int(target_value)
    target = db.execute("SELECT id FROM characters WHERE id = ? AND campaign_id = ?", (target_id, campaign["id"])).fetchone()
    if target is None or target_id == character_id:
        flash("El personaje seleccionado no es válido.", "error")
        return redirect(url_for("character_detail", character_id=character_id))
    try:
        db.execute("INSERT INTO character_relationships (character_id, related_character_id, relationship_type, description) VALUES (?, ?, ?, ?)", (character_id, target_id, relationship_type, request.form.get("description", "").strip()))
        db.commit()
        flash("Relación creada correctamente.", "success")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("Esta relación ya existe o no es válida.", "error")
    return redirect(url_for("character_detail", character_id=character_id))


@app.route("/characters/<int:character_id>/relationships/<int:relationship_id>/delete", methods=["POST"])
def relationship_delete(character_id, relationship_id):
    campaign = get_campaign()
    db = get_db()
    if db.execute("SELECT id FROM characters WHERE id = ? AND campaign_id = ?", (character_id, campaign["id"])).fetchone() is None:
        abort(404)
    db.execute("DELETE FROM character_relationships WHERE id = ? AND character_id = ?", (relationship_id, character_id))
    db.commit()
    flash("Relación eliminada.", "success")
    return redirect(url_for("character_detail", character_id=character_id))


@app.route("/factions")
def factions():
    campaign = get_campaign()
    rows = get_db().execute("""
        SELECT factions.*, COUNT(DISTINCT faction_memberships.id) AS member_count, COUNT(DISTINCT faction_locations.id) AS location_count
        FROM factions
        LEFT JOIN faction_memberships ON faction_memberships.faction_id = factions.id
        LEFT JOIN faction_locations ON faction_locations.faction_id = factions.id
        WHERE factions.campaign_id = ?
        GROUP BY factions.id ORDER BY factions.name COLLATE NOCASE
    """, (campaign["id"],)).fetchall()
    return render_template("factions/list.html", factions=rows, campaign=campaign)


@app.route("/factions/new", methods=["GET", "POST"])
def faction_new():
    campaign = get_campaign()
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("factions/form.html", faction=None)
        db.execute("""
            INSERT INTO factions (campaign_id, name, faction_type, summary, description, ideology, goals, hierarchy, secret_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (campaign["id"], name, request.form.get("faction_type", "Otra").strip() or "Otra", request.form.get("summary", "").strip(), request.form.get("description", "").strip(), request.form.get("ideology", "").strip(), request.form.get("goals", "").strip(), request.form.get("hierarchy", "").strip(), request.form.get("secret_notes", "").strip()))
        db.commit()
        flash("Facción creada correctamente.", "success")
        return redirect(url_for("factions"))
    return render_template("factions/form.html", faction=None)


@app.route("/factions/<int:faction_id>")
def faction_detail(faction_id):
    campaign = get_campaign()
    db = get_db()
    faction = get_faction_or_404(faction_id, campaign["id"])
    members = db.execute("""
        SELECT faction_memberships.*, characters.name, characters.ancestry, characters.occupation, characters.id AS character_id
        FROM faction_memberships JOIN characters ON characters.id = faction_memberships.character_id
        WHERE faction_memberships.faction_id = ? ORDER BY characters.name COLLATE NOCASE
    """, (faction_id,)).fetchall()
    locations_linked = db.execute("""
        SELECT faction_locations.*, locations.name, locations.category, locations.id AS location_id
        FROM faction_locations JOIN locations ON locations.id = faction_locations.location_id
        WHERE faction_locations.faction_id = ? ORDER BY locations.name COLLATE NOCASE
    """, (faction_id,)).fetchall()
    relationships = db.execute("""
        SELECT faction_relationships.*, factions.name AS related_name, factions.id AS related_id, factions.faction_type AS related_type
        FROM faction_relationships JOIN factions ON factions.id = faction_relationships.related_faction_id
        WHERE faction_relationships.faction_id = ? ORDER BY factions.name COLLATE NOCASE
    """, (faction_id,)).fetchall()
    available_characters = db.execute("""
        SELECT id, name FROM characters WHERE campaign_id = ? AND id NOT IN (
            SELECT character_id FROM faction_memberships WHERE faction_id = ?
        ) ORDER BY name COLLATE NOCASE
    """, (campaign["id"], faction_id)).fetchall()
    available_locations = db.execute("""
        SELECT id, name FROM locations WHERE campaign_id = ? AND id NOT IN (
            SELECT location_id FROM faction_locations WHERE faction_id = ?
        ) ORDER BY name COLLATE NOCASE
    """, (campaign["id"], faction_id)).fetchall()
    available_factions = db.execute("SELECT id, name FROM factions WHERE campaign_id = ? AND id != ? ORDER BY name COLLATE NOCASE", (campaign["id"], faction_id)).fetchall()
    return render_template("factions/detail.html", faction=faction, members=members, locations=locations_linked, relationships=relationships, available_characters=available_characters, available_locations=available_locations, available_factions=available_factions)


@app.route("/factions/<int:faction_id>/edit", methods=["GET", "POST"])
def faction_edit(faction_id):
    campaign = get_campaign()
    db = get_db()
    faction = get_faction_or_404(faction_id, campaign["id"])
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("factions/form.html", faction=faction)
        db.execute("""
            UPDATE factions SET name=?, faction_type=?, summary=?, description=?, ideology=?, goals=?, hierarchy=?, secret_notes=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND campaign_id=?
        """, (name, request.form.get("faction_type", "Otra").strip() or "Otra", request.form.get("summary", "").strip(), request.form.get("description", "").strip(), request.form.get("ideology", "").strip(), request.form.get("goals", "").strip(), request.form.get("hierarchy", "").strip(), request.form.get("secret_notes", "").strip(), faction_id, campaign["id"]))
        db.commit()
        flash("Facción actualizada.", "success")
        return redirect(url_for("faction_detail", faction_id=faction_id))
    return render_template("factions/form.html", faction=faction)


@app.route("/factions/<int:faction_id>/delete", methods=["POST"])
def faction_delete(faction_id):
    campaign = get_campaign()
    db = get_db()
    get_faction_or_404(faction_id, campaign["id"])
    db.execute("DELETE FROM factions WHERE id = ? AND campaign_id = ?", (faction_id, campaign["id"]))
    db.commit()
    flash("Facción eliminada.", "success")
    return redirect(url_for("factions"))


def faction_action_context(faction_id):
    campaign = get_campaign()
    faction = get_faction_or_404(faction_id, campaign["id"])
    return campaign, get_db(), faction


@app.route("/factions/<int:faction_id>/members", methods=["POST"])
def faction_member_create(faction_id):
    campaign, db, _ = faction_action_context(faction_id)
    character_value = request.form.get("character_id", "").strip()
    role = text_field("role")
    if not character_value.isdigit() or role is None:
        flash("Selecciona un personaje e indica un cargo válido.", "error")
    else:
        character_id = int(character_value)
        valid = db.execute("SELECT id FROM characters WHERE id=? AND campaign_id=?", (character_id, campaign["id"])).fetchone()
        if valid is None:
            flash("El personaje seleccionado no es válido.", "error")
        else:
            try:
                db.execute("INSERT INTO faction_memberships (faction_id, character_id, role, description) VALUES (?, ?, ?, ?)", (faction_id, character_id, role, request.form.get("description", "").strip()))
                db.commit()
                flash("Personaje vinculado a la facción.", "success")
            except sqlite3.IntegrityError:
                db.rollback()
                flash("Ese personaje ya está vinculado a la facción.", "error")
    return redirect(url_for("faction_detail", faction_id=faction_id))


@app.route("/factions/<int:faction_id>/members/<int:membership_id>/delete", methods=["POST"])
def faction_member_delete(faction_id, membership_id):
    _, db, _ = faction_action_context(faction_id)
    db.execute("DELETE FROM faction_memberships WHERE id=? AND faction_id=?", (membership_id, faction_id))
    db.commit()
    flash("Vínculo con el personaje eliminado.", "success")
    return redirect(url_for("faction_detail", faction_id=faction_id))


@app.route("/factions/<int:faction_id>/locations", methods=["POST"])
def faction_location_create(faction_id):
    campaign, db, _ = faction_action_context(faction_id)
    location_value = request.form.get("location_id", "").strip()
    relationship_type = text_field("relationship_type")
    if not location_value.isdigit() or relationship_type is None:
        flash("Selecciona una localización e indica un vínculo válido.", "error")
    else:
        location_id = int(location_value)
        valid = db.execute("SELECT id FROM locations WHERE id=? AND campaign_id=?", (location_id, campaign["id"])).fetchone()
        if valid is None:
            flash("La localización seleccionada no es válida.", "error")
        else:
            try:
                db.execute("INSERT INTO faction_locations (faction_id, location_id, relationship_type, description) VALUES (?, ?, ?, ?)", (faction_id, location_id, relationship_type, request.form.get("description", "").strip()))
                db.commit()
                flash("Localización vinculada a la facción.", "success")
            except sqlite3.IntegrityError:
                db.rollback()
                flash("Esa localización ya está vinculada a la facción.", "error")
    return redirect(url_for("faction_detail", faction_id=faction_id))


@app.route("/factions/<int:faction_id>/locations/<int:link_id>/delete", methods=["POST"])
def faction_location_delete(faction_id, link_id):
    _, db, _ = faction_action_context(faction_id)
    db.execute("DELETE FROM faction_locations WHERE id=? AND faction_id=?", (link_id, faction_id))
    db.commit()
    flash("Vínculo con la localización eliminado.", "success")
    return redirect(url_for("faction_detail", faction_id=faction_id))


@app.route("/factions/<int:faction_id>/relationships", methods=["POST"])
def faction_relationship_create(faction_id):
    campaign, db, _ = faction_action_context(faction_id)
    target_value = request.form.get("related_faction_id", "").strip()
    relationship_type = text_field("relationship_type")
    if not target_value.isdigit() or relationship_type is None:
        flash("Selecciona una facción e indica una relación válida.", "error")
    else:
        target_id = int(target_value)
        valid = db.execute("SELECT id FROM factions WHERE id=? AND campaign_id=?", (target_id, campaign["id"])).fetchone()
        if valid is None or target_id == faction_id:
            flash("La facción seleccionada no es válida.", "error")
        else:
            try:
                db.execute("INSERT INTO faction_relationships (faction_id, related_faction_id, relationship_type, description) VALUES (?, ?, ?, ?)", (faction_id, target_id, relationship_type, request.form.get("description", "").strip()))
                db.commit()
                flash("Relación entre facciones creada.", "success")
            except sqlite3.IntegrityError:
                db.rollback()
                flash("Esta relación ya existe o no es válida.", "error")
    return redirect(url_for("faction_detail", faction_id=faction_id))


@app.route("/factions/<int:faction_id>/relationships/<int:relationship_id>/delete", methods=["POST"])
def faction_relationship_delete(faction_id, relationship_id):
    _, db, _ = faction_action_context(faction_id)
    db.execute("DELETE FROM faction_relationships WHERE id=? AND faction_id=?", (relationship_id, faction_id))
    db.commit()
    flash("Relación entre facciones eliminada.", "success")
    return redirect(url_for("faction_detail", faction_id=faction_id))


def get_creature_or_404(creature_id, campaign_id):
    creature = get_db().execute("SELECT * FROM creatures WHERE id = ? AND campaign_id = ?", (creature_id, campaign_id)).fetchone()
    if creature is None:
        abort(404)
    return creature


def get_item_or_404(item_id, campaign_id):
    item = get_db().execute("SELECT * FROM items WHERE id = ? AND campaign_id = ?", (item_id, campaign_id)).fetchone()
    if item is None:
        abort(404)
    return item


def valid_optional_location(db, campaign_id):
    value = request.form.get("location_id", "").strip()
    location_id = int(value) if value.isdigit() else None
    if location_id is not None and db.execute("SELECT id FROM locations WHERE id = ? AND campaign_id = ?", (location_id, campaign_id)).fetchone() is None:
        abort(400)
    return location_id


def creature_values():
    return (
        request.form.get("creature_type", "Criatura").strip() or "Criatura",
        optional_int("level"),
        request.form.get("rarity", "Común").strip() or "Común",
        request.form.get("alignment", "").strip(),
        request.form.get("size", "").strip(),
        request.form.get("ancestry", "").strip(),
        request.form.get("summary", "").strip(),
        request.form.get("description", "").strip(),
        optional_int("armor_class"),
        optional_int("hit_points"),
        request.form.get("perception", "").strip(),
        request.form.get("saving_throws", "").strip(),
        request.form.get("skills", "").strip(),
        request.form.get("speeds", "").strip(),
        request.form.get("attacks", "").strip(),
        request.form.get("abilities", "").strip(),
        request.form.get("weaknesses", "").strip(),
        request.form.get("resistances", "").strip(),
        request.form.get("immunities", "").strip(),
        request.form.get("loot", "").strip(),
        request.form.get("image_url", "").strip(),
        request.form.get("secret_notes", "").strip(),
    )


def item_values():
    return (
        request.form.get("item_type", "Otro").strip() or "Otro",
        request.form.get("rarity", "Común").strip() or "Común",
        optional_int("level"),
        request.form.get("price", "").strip(),
        request.form.get("bulk", "").strip(),
        request.form.get("traits", "").strip(),
        request.form.get("summary", "").strip(),
        request.form.get("description", "").strip(),
        request.form.get("activation", "").strip(),
        request.form.get("effects", "").strip(),
        request.form.get("usage", "").strip(),
        request.form.get("owner", "").strip(),
        request.form.get("image_url", "").strip(),
        request.form.get("secret_notes", "").strip(),
    )


@app.route("/bestiary")
def bestiary():
    campaign = get_campaign()
    creatures = get_db().execute("""
        SELECT creatures.*, locations.name AS location_name FROM creatures
        LEFT JOIN locations ON locations.id = creatures.location_id
        WHERE creatures.campaign_id = ? ORDER BY creatures.name COLLATE NOCASE
    """, (campaign["id"],)).fetchall()
    return render_template("bestiary/list.html", creatures=creatures, campaign=campaign)


@app.route("/bestiary/new", methods=["GET", "POST"])
def creature_new():
    campaign = get_campaign()
    db = get_db()
    locations_for_form = character_locations(campaign["id"])
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("bestiary/form.html", creature=None, locations=locations_for_form)
        db.execute("""
            INSERT INTO creatures (campaign_id, location_id, name, creature_type, level, rarity, alignment, size, ancestry, summary, description, armor_class, hit_points, perception, saving_throws, skills, speeds, attacks, abilities, weaknesses, resistances, immunities, loot, image_url, secret_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (campaign["id"], valid_optional_location(db, campaign["id"]), name, *creature_values()))
        db.commit()
        flash("Criatura registrada correctamente.", "success")
        return redirect(url_for("bestiary"))
    return render_template("bestiary/form.html", creature=None, locations=locations_for_form)


@app.route("/bestiary/<int:creature_id>")
def creature_detail(creature_id):
    campaign = get_campaign()
    creature = get_creature_or_404(creature_id, campaign["id"])
    location = None
    if creature["location_id"]:
        location = get_db().execute("SELECT id, name FROM locations WHERE id = ? AND campaign_id = ?", (creature["location_id"], campaign["id"])).fetchone()
    return render_template("bestiary/detail.html", creature=creature, location=location)


@app.route("/bestiary/<int:creature_id>/edit", methods=["GET", "POST"])
def creature_edit(creature_id):
    campaign = get_campaign()
    db = get_db()
    creature = get_creature_or_404(creature_id, campaign["id"])
    locations_for_form = character_locations(campaign["id"])
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("bestiary/form.html", creature=creature, locations=locations_for_form)
        db.execute("""
            UPDATE creatures SET location_id=?, name=?, creature_type=?, level=?, rarity=?, alignment=?, size=?, ancestry=?, summary=?, description=?, armor_class=?, hit_points=?, perception=?, saving_throws=?, skills=?, speeds=?, attacks=?, abilities=?, weaknesses=?, resistances=?, immunities=?, loot=?, image_url=?, secret_notes=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND campaign_id=?
        """, (valid_optional_location(db, campaign["id"]), name, *creature_values(), creature_id, campaign["id"]))
        db.commit()
        flash("Criatura actualizada.", "success")
        return redirect(url_for("creature_detail", creature_id=creature_id))
    return render_template("bestiary/form.html", creature=creature, locations=locations_for_form)


@app.route("/bestiary/<int:creature_id>/delete", methods=["POST"])
def creature_delete(creature_id):
    campaign = get_campaign()
    db = get_db()
    get_creature_or_404(creature_id, campaign["id"])
    db.execute("DELETE FROM creatures WHERE id = ? AND campaign_id = ?", (creature_id, campaign["id"]))
    db.commit()
    flash("Criatura eliminada.", "success")
    return redirect(url_for("bestiary"))


@app.route("/items")
def items():
    campaign = get_campaign()
    rows = get_db().execute("""
        SELECT items.*, locations.name AS location_name FROM items
        LEFT JOIN locations ON locations.id = items.location_id
        WHERE items.campaign_id = ? ORDER BY items.name COLLATE NOCASE
    """, (campaign["id"],)).fetchall()
    return render_template("items/list.html", items=rows, campaign=campaign)


@app.route("/items/new", methods=["GET", "POST"])
def item_new():
    campaign = get_campaign()
    db = get_db()
    locations_for_form = character_locations(campaign["id"])
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("items/form.html", item=None, locations=locations_for_form)
        db.execute("""
            INSERT INTO items (campaign_id, location_id, name, item_type, rarity, level, price, bulk, traits, summary, description, activation, effects, usage, owner, image_url, secret_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (campaign["id"], valid_optional_location(db, campaign["id"]), name, *item_values()))
        db.commit()
        flash("Objeto registrado correctamente.", "success")
        return redirect(url_for("items"))
    return render_template("items/form.html", item=None, locations=locations_for_form)


@app.route("/items/<int:item_id>")
def item_detail(item_id):
    campaign = get_campaign()
    item = get_item_or_404(item_id, campaign["id"])
    location = None
    if item["location_id"]:
        location = get_db().execute("SELECT id, name FROM locations WHERE id = ? AND campaign_id = ?", (item["location_id"], campaign["id"])).fetchone()
    return render_template("items/detail.html", item=item, location=location)


@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
def item_edit(item_id):
    campaign = get_campaign()
    db = get_db()
    item = get_item_or_404(item_id, campaign["id"])
    locations_for_form = character_locations(campaign["id"])
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("El nombre es obligatorio.", "error")
            return render_template("items/form.html", item=item, locations=locations_for_form)
        db.execute("""
            UPDATE items SET location_id=?, name=?, item_type=?, rarity=?, level=?, price=?, bulk=?, traits=?, summary=?, description=?, activation=?, effects=?, usage=?, owner=?, image_url=?, secret_notes=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND campaign_id=?
        """, (valid_optional_location(db, campaign["id"]), name, *item_values(), item_id, campaign["id"]))
        db.commit()
        flash("Objeto actualizado.", "success")
        return redirect(url_for("item_detail", item_id=item_id))
    return render_template("items/form.html", item=item, locations=locations_for_form)


@app.route("/items/<int:item_id>/delete", methods=["POST"])
def item_delete(item_id):
    campaign = get_campaign()
    db = get_db()
    get_item_or_404(item_id, campaign["id"])
    db.execute("DELETE FROM items WHERE id = ? AND campaign_id = ?", (item_id, campaign["id"]))
    db.commit()
    flash("Objeto eliminado.", "success")
    return redirect(url_for("items"))


if __name__ == "__main__":
    app.run(debug=True)
