
from flask import Flask, render_template, request, jsonify
import sqlite3
from pathlib import Path

app = Flask(__name__)
DB = Path(__file__).with_name("estoque.db")


def conectar():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def iniciar_banco():
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL UNIQUE,
                categoria TEXT NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 0,
                minimo INTEGER NOT NULL DEFAULT 5,
                preco REAL NOT NULL DEFAULT 0
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                data TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(produto_id) REFERENCES produtos(id)
            )
        """)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.get("/api/resumo")
def resumo():
    with conectar() as con:
        total = con.execute(
            "SELECT COUNT(*) FROM produtos"
        ).fetchone()[0]
        baixo = con.execute(
            "SELECT COUNT(*) FROM produtos WHERE quantidade <= minimo"
        ).fetchone()[0]
        unidades = con.execute(
            "SELECT COALESCE(SUM(quantidade), 0) FROM produtos"
        ).fetchone()[0]
        movimentos = con.execute(
            "SELECT COUNT(*) FROM movimentacoes"
        ).fetchone()[0]

    return jsonify(produtos=total, estoque_baixo=baixo,
                   unidades=unidades, movimentacoes=movimentos)


@app.get("/api/produtos")
def listar_produtos():
    busca = request.args.get("busca", "").strip()
    with conectar() as con:
        produtos = con.execute("""
            SELECT * FROM produtos
            WHERE nome LIKE ? OR codigo LIKE ? OR categoria LIKE ?
            ORDER BY id DESC
        """, (f"%{busca}%", f"%{busca}%", f"%{busca}%")).fetchall()
    return jsonify([dict(p) for p in produtos])


@app.post("/api/produtos")
def cadastrar_produto():
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()
    codigo = str(dados.get("codigo", "")).strip()
    categoria = str(dados.get("categoria", "")).strip()

    try:
        quantidade = int(dados.get("quantidade", 0))
        minimo = int(dados.get("minimo", 5))
        preco = float(dados.get("preco", 0))
        if (not nome or not codigo or not categoria or
                quantidade < 0 or minimo < 0 or preco < 0):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify(erro="Preencha os campos corretamente."), 400

    try:
        with conectar() as con:
            cur = con.execute("""
                INSERT INTO produtos
                (nome, codigo, categoria, quantidade, minimo, preco)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome, codigo, categoria, quantidade, minimo, preco))
            produto_id = cur.lastrowid
            if quantidade > 0:
                con.execute("""
                    INSERT INTO movimentacoes (produto_id, tipo, quantidade)
                    VALUES (?, 'Entrada inicial', ?)
                """, (produto_id, quantidade))
        return jsonify(mensagem="Produto cadastrado!"), 201
    except sqlite3.IntegrityError:
        return jsonify(erro="Esse código de produto já existe."), 409


@app.post("/api/movimentacoes")
def movimentar():
    dados = request.get_json(silent=True) or {}
    try:
        produto_id = int(dados.get("produto_id", 0))
        quantidade = int(dados.get("quantidade", 0))
        tipo = dados.get("tipo")
        if quantidade <= 0 or tipo not in ("entrada", "saida"):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify(erro="Movimentação inválida."), 400

    with conectar() as con:
        produto = con.execute(
            "SELECT * FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()
        if produto is None:
            return jsonify(erro="Produto não encontrado."), 404

        nova = produto["quantidade"] + (
            quantidade if tipo == "entrada" else -quantidade
        )
        if nova < 0:
            return jsonify(erro="Estoque insuficiente."), 400

        con.execute(
            "UPDATE produtos SET quantidade = ? WHERE id = ?",
            (nova, produto_id)
        )
        con.execute("""
            INSERT INTO movimentacoes (produto_id, tipo, quantidade)
            VALUES (?, ?, ?)
        """, (produto_id, tipo, quantidade))

    return jsonify(mensagem="Estoque atualizado!")


@app.get("/api/movimentacoes")
def listar_movimentacoes():
    with conectar() as con:
        rows = con.execute("""
            SELECT m.id, p.nome, m.tipo, m.quantidade, m.data
            FROM movimentacoes m
            JOIN produtos p ON p.id = m.produto_id
            ORDER BY m.id DESC LIMIT 20
        """).fetchall()
    return jsonify([dict(r) for r in rows])


iniciar_banco()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)