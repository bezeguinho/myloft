@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: 
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email').lower()).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            
            # --- SE A CONTA ESTIVER BLOQUEADA, MANDA PARA A PÁGINA DE PAGAMENTO ---
            if not user.conta_ativa:
                return redirect(url_for('conta_suspensa'))
                
            login_user(user)
            return redirect(url_for('index'))
        flash("Email ou Password incorretos.", "danger")
    return render_template('login.html')

# NOVA ROTA: PÁGINA DE SUSPENSÃO
@app.route("/suspenso")
def conta_suspensa():
    return render_template("suspenso.html")