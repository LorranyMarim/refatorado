<?php
session_start();
if (isset($_SESSION['loggedin']) && $_SESSION['loggedin'] === true) {
    header("Location: dashboard.php");
    exit();
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Login - SENAI</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="../assets/css/style.css">
</head>
<body id="page-login">
  
  <div id="main-container" class="login-container">
    
    <img id="logo-senai" src="../assets/logo_azul.png" alt="Logo" class="senai-logo">

    <form id="login-form" action="../backend/login.php" method="POST" autocomplete="off" novalidate>
      <p id="form-error" class="error-message" style="display:none;color:#d9534f;margin-bottom:10px;"></p>

      <div id="group-instituicao" class="input-group">
        <label for="instituicao">Instituição:</label>
        <select id="instituicao" name="instituicao_id" required disabled>
          <option value="">Carregando instituições...</option>
        </select>
      </div>

      <div id="group-username" class="input-group">
        <label for="username">Usuário:</label>
        <input
          type="text"
          id="username"
          name="username"
          required
          minlength="4"
          maxlength="50"
          pattern="^[^<>'\"]+$"
          autocomplete="username"
        >
      </div>

      <div id="group-password" class="input-group">
        <label for="password">Senha:</label>
        <input
          type="password"
          id="password"
          name="password"
          required
          minlength="4"
          maxlength="50"
          autocomplete="current-password"
        >
      </div>

      <button id="btn-submit" type="submit" disabled>Entrar</button>

      <?php
        if (isset($_GET['erro'])) {
          echo '<input type="hidden" id="errcode" value="'.htmlspecialchars($_GET['erro']).'">';
        }
      ?>
    </form>
  </div>

  <script>
    document.addEventListener("DOMContentLoaded", function () {
      const API_INST_URL = "http://localhost:8000/api/instituicoes";

      const form = document.getElementById("login-form");
      
      const instSelect = document.getElementById("instituicao");
      const userInput = document.getElementById("username");
      const passInput = document.getElementById("password");
      const submitBtn = document.getElementById("btn-submit");
      const errP = document.getElementById("form-error");

      const minLen = 4;
      const maxLen = 50;
      const forbidden = /[<>'"]/;

      function showError(msg) {
        errP.textContent = msg;
        errP.style.display = "block";
      }
      function clearError() {
        errP.textContent = "";
        errP.style.display = "none";
      }

      (function handleBackendError() {
        const code = document.getElementById("errcode")?.value ||
                     new URLSearchParams(location.search).get("erro");
        if (!code) return;
        const map = {
          valid: "Dados inválidos.",
          limite: "Muitas tentativas. Tente novamente em alguns minutos.",
          auth: "Usuário ou senha incorretos.",
          inst: "Você não tem acesso à instituição selecionada.",
          inst_invalida: "Instituição inválida."
        };
        showError(map[code] || "Erro ao fazer login.");
      })();

      (async function carregarInstituicoes() {
        try {
          const res = await fetch(API_INST_URL);
          if (!res.ok) throw new Error("HTTP " + res.status);
          const lista = await res.json(); 
          instSelect.innerHTML = '<option value="">Selecione...</option>';
          lista.forEach(i => {
            const opt = document.createElement("option");
            opt.value = i._id;
            opt.textContent = i.nome || "(sem nome)";
            instSelect.appendChild(opt);
          });

          const last = localStorage.getItem("last_instituicao_id");
          if (last && instSelect.querySelector(`option[value="${last}"]`)) {
            instSelect.value = last;
          }

          instSelect.disabled = false;
          submitBtn.disabled = false;
        } catch (e) {
          console.error("Falha ao carregar instituições:", e);
          instSelect.innerHTML = '<option value="">(erro ao carregar)</option>';
          instSelect.disabled = true;
          submitBtn.disabled = true;
          showError("Não foi possível carregar as instituições. Verifique a API.");
        }
      })();

      instSelect.addEventListener("change", () => {
        clearError();
        if (instSelect.value) {
          localStorage.setItem("last_instituicao_id", instSelect.value);
        }
      });

      form.addEventListener("submit", function (e) {
        clearError();

        if (!instSelect.value) {
          e.preventDefault();
          showError("Selecione uma instituição.");
          instSelect.focus();
          return;
        }

        const user = (userInput.value || "").trim();
        if (!user) {
          e.preventDefault(); showError("Preencha o campo usuário."); userInput.focus(); return;
        }
        if (user.length < minLen) {
          e.preventDefault(); showError(`Usuário deve ter no mínimo ${minLen} caracteres.`); userInput.focus(); return;
        }
        if (user.length > maxLen) {
          e.preventDefault(); showError(`Usuário deve ter no máximo ${maxLen} caracteres.`); userInput.focus(); return;
        }
        if (forbidden.test(user)) {
          e.preventDefault(); showError("Usuário contém caracteres inválidos."); userInput.focus(); return;
        }

        const pass = passInput.value || "";
        if (!pass) {
          e.preventDefault(); showError("Preencha o campo senha."); passInput.focus(); return;
        }
        if (pass.length < minLen) {
          e.preventDefault(); showError(`Senha deve ter no mínimo ${minLen} caracteres.`); passInput.focus(); return;
        }
        if (pass.length > maxLen) {
          e.preventDefault(); showError(`Senha deve ter no máximo ${maxLen} caracteres.`); passInput.focus(); return;
        }
        if (forbidden.test(pass)) {
          e.preventDefault(); showError("Senha contém caracteres inválidos."); passInput.focus(); return;
        }
      });

      [userInput, passInput].forEach(inp => {
        inp.addEventListener("input", clearError);
      });
    });
  </script>
</body>
</html>