@app.route("/admin/toggle_admin/<int:user_id>")
@login_required
def toggle_admin_role(user_id):
    # Só um Admin pode mudar cargos
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    user_alvo = User.query.get(user_id)
    # Segurança: Não podes retirar Admin a ti próprio para não ficares trancado fora
    if user_alvo and user_alvo.id != current_user.id:
        user_alvo.is_admin = not user_alvo.is_admin
        db.session.commit()
        cargo = "ADMINISTRADOR" if user_alvo.is_admin else "UTILIZADOR COMUM"
        flash(f"O cargo de {user_alvo.email} foi alterado para {cargo}.", "success")
    
    return redirect(url_for('admin_dashboard'))