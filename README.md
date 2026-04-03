MYLOFT
======

Aplicação de gestão de pombos-correio pensada para **desktop e mobile**.

Inclui:
- Versão **desktop** (janela Tkinter em Python).
- Versão **web responsiva** (Flask + HTML/CSS/Bootstrap) que funciona bem em computador e telemóvel.

Requisitos
---------
- Python 3.10 ou superior instalado no Windows
- Dependências Python listadas em `requirements.txt`

Instalação das dependências
---------------------------
No PowerShell, dentro da pasta do projeto (`c:\Users\jps_g\Contacts\myloft`), execute:

```powershell
pip install -r requirements.txt
```

Logo da aplicação
-----------------
- Coloque uma imagem de uma pomba na pasta `static/img` com o nome **`myloft_logo.png`**.
- Tamanho recomendado: aproximadamente 64x64 píxeis.
- Se a imagem não existir ou der erro ao carregar, a aplicação mostrará apenas o texto `MYLOFT`.

Como executar a versão desktop (Tkinter)
----------------------------------------
Ainda no PowerShell, dentro da pasta do projeto, execute:

```powershell
python .\main.py
```

Como executar a versão web (desktop + mobile)
--------------------------------------------
No PowerShell, dentro da pasta do projeto, execute:

```powershell
python .\app.py
```

Depois abra o navegador (no computador ou telemóvel na mesma rede) e vá a:

```text
http://127.0.0.1:5000
```

Irá ver:
- Barra no topo com o logo `MYLOFT` no canto superior esquerdo.
- Menus responsivos (que viram “hamburger” no telemóvel):
  - LISTA DE POMBOS (REPRODUTORES, VOADORES, EXCLUÍDOS, TODOS OS POMBOS)
  - GESTÃO DE POMBOS (INSERIR, EDITAR, OCULTAR, APAGAR)
  - PEDIGREE (NUMÉRO DO POMBO, VER LISTA DE POMBOS)
  - SAIR

Neste momento, os menus da versão web ainda não têm lógica por trás; servem como ecrã principal base para evoluirmos o MYLOFT.

