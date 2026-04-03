import tkinter as tk
from tkinter import messagebox, ttk

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


class MyLoftApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MYLOFT")
        self.geometry("900x600")
        # Fundo azul um pouco mais escuro
        self.configure(background="#d1e4ff")

        self._logo_image = None

        style = ttk.Style()
        style.configure('Menu', font=('Segoe UI', 15, 'bold'))
        self._create_logo_area()
        self._create_menu_bar()
        self._create_main_title()

    def _create_logo_area(self):
        # Barra superior (logotipo) bem alta
        top_frame = tk.Frame(self, height=240, bg="#d1e4ff")
        top_frame.pack(side=tk.TOP, fill=tk.X)
        top_frame.pack_propagate(False)

        logo_frame = tk.Frame(top_frame, bg="#d1e4ff")
        logo_frame.pack(side=tk.LEFT, padx=10, pady=10)

        # Tenta carregar a imagem 'myloft_logo.png' na pasta do projeto
        if Image and ImageTk:
            try:
                image = Image.open("myloft_logo.png")
                image = image.resize((64, 64))
                self._logo_image = ImageTk.PhotoImage(image)
                logo_label = tk.Label(logo_frame, image=self._logo_image, bg="#d1e4ff")
                logo_label.pack(side=tk.LEFT)
            except Exception:
                pass

        # Mantém apenas o logotipo; o texto principal fica no centro do ecrã

    def _create_menu_bar(self):
        # Menus principais ~25% maiores (submenus mantêm-se)
        menubar = tk.Menu(self, tearoff=0, font=("Segoe UI", 15))

        # LISTA DE POMBOS (submenus ligeiramente mais pequenos)
        lista_menu = tk.Menu(menubar, tearoff=0, font=("Segoe UI", 10))
        lista_menu.add_command(label="REPRODUTORES", command=self._on_reprodutores)
        lista_menu.add_separator()
        lista_menu.add_command(label="VOADORES", command=self._on_voadores)
        lista_menu.add_separator()
        lista_menu.add_command(label="EXCLUÍDOS", command=self._on_excluidos)
        lista_menu.add_separator()
        lista_menu.add_command(label="TODOS OS POMBOS", command=self._on_todos_pombos)
        menubar.add_cascade(label="  LISTA DE POMBOS  ", menu=lista_menu)

        # GESTÃO DE POMBOS
        gestao_menu = tk.Menu(menubar, tearoff=0, font=("Segoe UI", 10))
        gestao_menu.add_command(label="INSERIR", command=self._on_inserir)
        gestao_menu.add_separator()
        gestao_menu.add_command(label="EDITAR", command=self._on_editar)
        gestao_menu.add_separator()
        gestao_menu.add_command(label="OCULTAR", command=self._on_ocultar)
        gestao_menu.add_separator()
        gestao_menu.add_command(label="APAGAR", command=self._on_apagar)
        menubar.add_cascade(label="  GESTÃO DE POMBOS  ", menu=gestao_menu)

        # PEDIGREE
        pedigree_menu = tk.Menu(menubar, tearoff=0, font=("Segoe UI", 10))
        pedigree_menu.add_command(label="NUMÉRO DO POMBO", command=self._on_pedigree_numero)
        pedigree_menu.add_separator()
        pedigree_menu.add_command(label="VER LISTA DE POMBOS", command=self._on_pedigree_lista)
        menubar.add_cascade(label="  PEDIGREE  ", menu=pedigree_menu)

        # OS MEUS DADOS
        meus_dados_menu = tk.Menu(menubar, tearoff=0, font=("Segoe UI", 10))
        meus_dados_menu.add_command(label="VER DADOS", command=self._on_ver_meus_dados)
        meus_dados_menu.add_separator()
        meus_dados_menu.add_command(label="EDITAR DADOS", command=self._on_editar_meus_dados)
        menubar.add_cascade(label="  OS MEUS DADOS  ", menu=meus_dados_menu)

        # SAIR
        menubar.add_command(label="  SAIR  ", command=self._on_sair)

        self.config(menu=menubar)

    def _create_main_title(self):
        center_frame = tk.Frame(self, bg="#d1e4ff")
        # Ocupa o ecrã abaixo da barra do logotipo e centra o texto em altura
        center_frame.pack(expand=True, fill=tk.BOTH)

        title_label = tk.Label(
            center_frame,
            text="MYLOFT - Gestão de Colónias",
            font=("Segoe UI", 28, "bold"),
            bg="#d1e4ff",
            fg="#000000",
        )
        # Expande mas com MUITO mais espaço em baixo para subir visualmente o texto
        title_label.pack(expand=True, pady=(0, 240))

    # Callbacks dos menus (por agora apenas mensagens de exemplo)
    def _on_reprodutores(self):
        self._show_info("Reprodutores", "Aqui irá aparecer a lista de reprodutores.")

    def _on_voadores(self):
        self._show_info("Voadores", "Aqui irá aparecer a lista de voadores.")

    def _on_excluidos(self):
        self._show_info("Excluídos", "Aqui irá aparecer a lista de pombos excluídos.")

    def _on_todos_pombos(self):
        self._show_info("Todos os Pombos", "Aqui irá aparecer a lista de todos os pombos.")

    def _on_inserir(self):
        self._show_info("Inserir Pombo", "Ecrã para inserir um novo pombo.")

    def _on_editar(self):
        self._show_info("Editar Pombo", "Ecrã para editar dados de um pombo.")

    def _on_ocultar(self):
        self._show_info("Ocultar Pombo", "Função para ocultar um pombo.")

    def _on_apagar(self):
        self._show_info("Apagar Pombo", "Função para apagar um pombo.")

    def _on_pedigree_numero(self):
        self._show_info("Pedigree por Número", "Pesquisar pedigree pelo número do pombo.")

    def _on_pedigree_lista(self):
        self._show_info("Lista de Pombos (Pedigree)", "Escolher o pombo a partir da lista.")

    def _on_ver_meus_dados(self):
        self._show_info("Os Meus Dados", "Ecrã para visualizar os seus dados pessoais.")

    def _on_editar_meus_dados(self):
        self._show_info("Os Meus Dados", "Ecrã para editar os seus dados pessoais.")

    def _on_sair(self):
        if messagebox.askyesno("Sair", "Tem a certeza que quer sair?"):
            self.destroy()

    def _show_info(self, titulo: str, mensagem: str):
        messagebox.showinfo(titulo, mensagem)


def main():
    app = MyLoftApp()
    app.mainloop()


if __name__ == "__main__":
    main()

