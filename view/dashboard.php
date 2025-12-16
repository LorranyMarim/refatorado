<?php
require_once("../config/verifica_login.php");
?>

<!DOCTYPE html>
<html lang="pt-BR" id="page-dashboard-html">

<head id="page-head">
    <meta charset="UTF-8" id="meta-charset">
    <meta name="viewport" content="width=device-width, initial-scale=1.0" id="meta-viewport">
    <title id="page-title">Dashboard de Turmas SENAI</title>
    <script src="https://cdn.tailwindcss.com" id="script-tailwind"></script>
    <link rel="stylesheet" href="../assets/css/style.css" id="link-css-custom">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" id="link-css-fontawesome">
</head>

<body id="page-body">
    <div class="dashboard-container" id="container-main-wrapper">
        
        <aside class="sidebar" id="sidebar-main">
            <div class="sidebar-header" id="sidebar-header-container">
                <img src="../assets/logo.png" alt="Logo SENAI" class="sidebar-logo" id="sidebar-logo-img">
                <h3 id="sidebar-title-text">Menu Principal</h3>
            </div>
            <nav class="sidebar-nav" id="sidebar-nav-container">
                <ul id="sidebar-list-main">
                    <li id="item-dashboard">
                        <a href="dashboard.php" class="active" id="link-dashboard">
                            <i class="fas fa-chart-line" id="icon-dashboard"></i> Dashboard
                        </a>
                    </li>
                    <li id="item-cursos">
                        <a href="gestao_cursos.php" id="link-cursos">
                            <i class="fas fa-book" id="icon-cursos"></i> Gestão de Cursos
                        </a>
                    </li>
                    <li id="item-turmas">
                        <a href="gestao_turmas.php" id="link-turmas">
                            <i class="fas fa-users" id="icon-turmas"></i> Gestão de Turmas
                        </a>
                    </li>
                    <li id="item-instrutores">
                        <a href="gestao_instrutores.php" id="link-instrutores">
                            <i class="fas fa-chalkboard-teacher" id="icon-instrutores"></i> Gestão de Instrutores
                        </a>
                    </li>
                    <li id="item-empresas">
                        <a href="gestao_empresas.php" id="link-empresas">
                            <i class="fas fa-building" id="icon-empresas"></i> Gestão de Empresas
                        </a>
                    </li>
                    <li id="item-ucs">
                        <a href="gestao_unidades_curriculares.php" id="link-ucs">
                            <i class="fas fa-graduation-cap" id="icon-ucs"></i> Gestão de UCs
                        </a>
                    </li>
                    <li id="item-calendario">
                        <a href="gestao_calendario.php" id="link-calendario">
                            <i class="fas fa-calendar-alt" id="icon-calendario"></i> Gestão de Calendários
                        </a>
                    </li>
                    
                    <li id="nav-relatorios" class="has-submenu">
                        <a href="#" class="submenu-toggle" aria-expanded="false" aria-controls="submenu-relatorios" id="toggle-relatorios">
                            <span id="span-relatorios-text">
                                <i class="fas fa-file-alt" id="icon-relatorios"></i> Relatórios
                            </span>
                            <i class="fas fa-chevron-right caret" aria-hidden="true" id="caret-relatorios"></i>
                        </a>
                        <ul class="submenu" id="submenu-relatorios">
                            <li id="item-relatorio-disp">
                                <a href="relatorio_disponibilidade_instrutor.php" id="link-relatorio-disp">Disponibilidade de Instrutor</a>
                            </li>
                        </ul>
                    </li>

                    <li id="nav-config" class="has-submenu">
                        <a href="#" class="submenu-toggle" aria-expanded="false" aria-controls="submenu-config" id="toggle-config">
                            <span id="span-config-text">
                                <i class="fas fa-tools" id="icon-config"></i> Configuração
                            </span>
                            <i class="fas fa-chevron-right caret" aria-hidden="true" id="caret-config"></i>
                        </a>
                        <ul class="submenu" id="submenu-config">
                            <li id="item-config-usuarios">
                                <a href="configuracao_usuarios.php" id="link-config-usuarios"> Usuários</a>
                            </li>
                        </ul>
                    </li>

                    <li id="item-logout">
                        <a href="../backend/logout.php" id="link-logout">
                            <i class="fas fa-sign-out-alt" id="icon-logout"></i> Sair
                        </a>
                    </li>
                </ul>
            </nav>
        </aside>

        <main class="main-content" id="main-content-area">
            <button class="menu-toggle" id="menu-toggle">
                <i class="fas fa-bars" id="icon-menu-toggle"></i>
            </button>
            
            <header class="main-header" id="header-main-content">
                <h1 id="title-dashboard-main">Dashboard</h1>
            </header>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8" id="grid-metrics-cards">
                
                <div class="bg-blue-500 text-white p-6 rounded-lg shadow-md flex items-center justify-between" id="card-metric-total-turmas">
                    <div id="wrapper-total-turmas">
                        <div class="text-2xl font-bold" id="totalTurmas">0</div>
                        <div class="text-sm" id="label-total-turmas">Total de Turmas</div>
                    </div>
                    <i class="fas fa-users text-4xl opacity-75" id="icon-metric-total-turmas"></i>
                </div>

                <div class="bg-green-500 text-white p-6 rounded-lg shadow-md flex items-center justify-between" id="card-metric-total-alunos">
                    <div id="wrapper-total-alunos">
                        <div class="text-2xl font-bold" id="totalAlunos">0</div>
                        <div class="text-sm" id="label-total-alunos">Total de Alunos</div>
                    </div>
                    <i class="fas fa-user-graduate text-4xl opacity-75" id="icon-metric-total-alunos"></i>
                </div>

                <div class="bg-yellow-500 text-white p-6 rounded-lg shadow-md flex items-center justify-between" id="card-metric-turmas-ativas">
                    <div id="wrapper-turmas-ativas">
                        <div class="text-2xl font-bold" id="turmasAtivas">0</div>
                        <div class="text-sm" id="label-turmas-ativas">Turmas Ativas</div>
                    </div>
                    <i class="fas fa-play-circle text-4xl opacity-75" id="icon-metric-turmas-ativas"></i>
                </div>

                <div class="bg-red-500 text-white p-6 rounded-lg shadow-md flex items-center justify-between" id="card-metric-turmas-incompletas">
                    <div id="wrapper-turmas-incompletas">
                        <div class="text-2xl font-bold" id="turmasIncompletas">0</div>
                        <div class="text-sm" id="label-turmas-incompletas">UCs sem Instrutor</div>
                    </div>
                    <i class="fas fa-exclamation-triangle text-4xl opacity-75" id="icon-metric-turmas-incompletas"></i>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8" id="grid-charts-section">
                <div class="bg-gray-50 p-6 rounded-lg shadow-md" id="card-chart-turno">
                    <h2 class="text-xl font-semibold text-gray-700 mb-4" id="title-chart-turno">Distribuição por Turno</h2>
                    <div id="distribuicaoTurno" class="space-y-2">
                        <canvas id="chartjs-bar" height="120"></canvas>
                    </div>
                </div>
                
                <div class="bg-gray-50 p-6 rounded-lg shadow-md" id="card-chart-area">
                    <h2 class="text-xl font-semibold text-gray-700 mb-4" id="title-chart-area">Distribuição por Área</h2>
                    <div id="distribuicaoArea" class="space-y-2">
                        <canvas id="chartjs-pie" height="180"></canvas>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6" id="grid-lists-section">
                
                <div class="bg-gray-50 p-6 rounded-lg shadow-md" id="card-list-proximas">
                    <h2 class="text-xl font-semibold text-gray-700 mb-4" id="title-list-proximas">Próximas Turmas (Início em 30 dias)</h2>
                    <ul id="proximasTurmas" class="list-disc list-inside space-y-1 text-gray-600">
                    </ul>
                    <p id="noProximasTurmas" class="text-gray-500 italic hidden">Nenhuma turma iniciando nos próximos 30 dias.</p>
                </div>

                <div class="bg-gray-50 p-6 rounded-lg shadow-md" id="card-list-incompletas">
                    <h2 class="text-xl font-semibold text-gray-700 mb-4" id="title-list-incompletas">Turmas com Dados Incompletos</h2>
                    <ul id="turmasComDadosVazios" class="list-disc list-inside space-y-1 text-gray-600">
                    </ul>
                    <p id="noTurmasComDadosVazios" class="text-gray-500 italic hidden">Nenhuma turma com dados incompletos.</p>
                </div>
            </div>

        </main>
    </div>

    <script src="../assets/js/geral_script.js" id="script-js-geral"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js" id="script-js-chartjs-lib"></script>
    <script src="../assets/js/dashboard_script.js" id="script-js-dashboard-custom"></script>
</body>

</html>