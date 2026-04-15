# --- Certifica-te que estas linhas estão no topo do teu main.py ---
import os
from werkzeug.utils import secure_filename

# ... (restante código de configuração) ...

@app.route("/meus-dados/ver")
@login_required
def ver_dados():
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    if not utilizador:
        return redirect(url_for('inserir_dados'))
    return render_template("meus_dados_ver.html", utilizador=utilizador)

@app.route("/meus-dados/inserir", methods=['GET', 'POST'])
@login_required
def inserir_dados():
    if Utilizador.query.filter_by(user_id=current_user.id).first():
        return redirect(url_for('editar_dados'))
    if request.method == 'POST':
        novo = Utilizador(
            nome=request.form.get('nome'),
            localberry=request.form.get('localidade'),
            telefone=request.form.get('telefone'),
            email=request.form.get('email'),
            user_id=current_user.id
        )
        foto = request.files.get('foto')
        if foto and foto.filename:
            filename = secure_filename(foto.filename)
            # Cria a pasta se não existir
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            novo.foto = 'uploads/' + filename
        
        db.session.add(novo)
        db.session.commit()
        flash('Dados guardados com sucesso!', 'success')
        return redirect(url_for('ver_dados'))
    return render_template("meus_dados_form.html")

@app.route("/meus-dados/editar", methods=['GET', 'POST'])
@login_required
def editar_dados():
    utilizador = Utilizador.query.filter_by(user_id=current_user.id).first()
    if request.method == 'POST':
        utilizador.nome = request.form.get('nome')
        utilizador.localberry = request.form.get('localidade')
        utilizador.telefone = request.form.get('telefone')
        utilizador.email = request.form.get('email')
        
        foto = request.files.get('foto')
        if foto and foto.filename:
            filename = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            utilizador.foto = 'uploads/' + filename
            
        db.session.commit()
        flash('Dados atualizados!', 'success')
        return redirect(url_for('ver_dados'))
    return render_template("meus_dados_form.html", utilizador=utilizador, modo_edicao=True)