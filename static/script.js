
const $ = (id) => document.getElementById(id);
let tipoMovimento = "";

async function api(url, options = {}) {
    const resposta = await fetch(url, {
        ...options,
        headers: { "Content-Type": "application/json", ...options.headers }
    });
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.erro || "Ocorreu um erro.");
    return dados;
}

function abrirModal() {
    $("erroForm").textContent = "";
    $("formProduto").reset();
    $("modalProduto").showModal();
}
function fecharModal() { $("modalProduto").close(); }
function fecharMovimento() { $("modalMovimento").close(); }

async function carregarResumo() {
    const r = await api("/api/resumo");
    $("totalProdutos").textContent = r.produtos;
    $("estoqueBaixo").textContent = r.estoque_baixo;
    $("totalUnidades").textContent = r.unidades;
    $("totalMovimentos").textContent = r.movimentacoes;
}

function criarCelula(valor, classe = "") {
    const td = document.createElement("td");
    td.textContent = valor ?? "";
    if (classe) td.className = classe;
    return td;
}

async function carregarProdutos() {
    try {
        const produtos = await api("/api/produtos?busca=" +
            encodeURIComponent($("busca").value));
        const tbody = $("listaProdutos");
        tbody.replaceChildren();
        $("semProdutos").hidden = produtos.length > 0;

        produtos.forEach(p => {
            const tr = document.createElement("tr");
            const nome = document.createElement("td");
            const strong = document.createElement("span");
            strong.className = "product-name";
            strong.textContent = p.nome;
            nome.append(strong);
            tr.append(nome, criarCelula(p.codigo), criarCelula(p.categoria),
                criarCelula(p.quantidade),
                criarCelula(Number(p.preco).toLocaleString("pt-BR",
                    { style: "currency", currency: "BRL" })));

            const status = document.createElement("td");
            const badge = document.createElement("span");
            badge.className = "badge " + (p.quantidade <= p.minimo ? "low" : "ok");
            badge.textContent = p.quantidade <= p.minimo ? "Estoque baixo" : "Disponível";
            status.append(badge);
            tr.append(status);

            const acoes = document.createElement("td");
            const grupo = document.createElement("div");
            grupo.className = "actions";
            [["＋ Entrada", "entrada"], ["− Saída", "saida"]].forEach(([texto, tipo]) => {
                const btn = document.createElement("button");
                btn.className = "small-btn";
                btn.textContent = texto;
                btn.addEventListener("click", () => abrirMovimento(p, tipo));
                grupo.append(btn);
            });
            acoes.append(grupo);
            tr.append(acoes);
            tbody.append(tr);
        });
    } catch (e) {
        alert(e.message);
    }
}

function abrirMovimento(produto, tipo) {
    tipoMovimento = tipo;
    $("formMovimento").reset();
    $("formMovimento").elements.produto_id.value = produto.id;
    $("nomeMovimento").value = produto.nome;
    $("tituloMovimento").textContent =
        tipo === "entrada" ? "Registrar entrada" : "Registrar saída";
    $("erroMovimento").textContent = "";
    $("modalMovimento").showModal();
}

$("formProduto").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const dados = Object.fromEntries(f.entries());
    for (const campo of ["quantidade", "minimo", "preco"]) {
        dados[campo] = Number(dados[campo]);
    }
    try {
        await api("/api/produtos", {
            method: "POST", body: JSON.stringify(dados)
        });
        fecharModal();
        await atualizar();
    } catch (erro) {
        $("erroForm").textContent = erro.message;
    }
});

$("formMovimento").addEventListener("submit", async (e) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    const dados = {
        produto_id: Number(f.get("produto_id")),
        quantidade: Number(f.get("quantidade")),
        tipo: tipoMovimento
    };
    try {
        await api("/api/movimentacoes", {
            method: "POST", body: JSON.stringify(dados)
        });
        fecharMovimento();
        await atualizar();
    } catch (erro) {
        $("erroMovimento").textContent = erro.message;
    }
});

async function atualizar() {
    await Promise.all([carregarResumo(), carregarProdutos(), carregarMovimentos()]);
}

async function carregarMovimentos() {
    const movimentos = await api("/api/movimentacoes");
    const tbody = $("listaMovimentos");
    tbody.replaceChildren();

    movimentos.forEach(m => {
        const tr = document.createElement("tr");
        tr.append(
            criarCelula(m.nome),
            criarCelula(m.tipo === "entrada" ? "Entrada" :
                m.tipo === "saida" ? "Saída" : "Estoque inicial"),
            criarCelula(m.quantidade),
            criarCelula(new Date(m.data.replace(" ", "T") + "Z")
                .toLocaleString("pt-BR"))
        );
        tbody.append(tr);
    });
}

atualizar().catch(e => alert("Não foi possível carregar o sistema: " + e.message));