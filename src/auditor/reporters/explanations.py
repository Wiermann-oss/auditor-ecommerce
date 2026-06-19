"""
Explicações em linguagem de negócio para cada tipo de falha.
Converte detalhes técnicos em impacto real para a loja.
"""

from __future__ import annotations

import re
from typing import Optional


def explain_failure(
    check_id: str,
    check_name: str,
    detail: Optional[str],
    value: Optional[float] = None,
    threshold: Optional[float] = None,
    unit: Optional[str] = None,
) -> str:
    """Retorna explicação em português de negócio para uma falha."""
    fn = _HANDLERS.get(check_id) or _flow_or_popup_handler
    return fn(check_id, check_name, detail, value, threshold, unit)


# ── Handlers por check_id ─────────────────────────────────────────────────────

def _http_status(check_id, check_name, detail, value, threshold, unit) -> str:
    code = int(value) if value else 0
    if code == 404:
        return (
            "A URL não existe — visitantes que tentarem acessar esta página verão uma "
            "tela de erro vazia. Links em anúncios, e-mails ou outras páginas da loja "
            "que apontem para cá estão quebrados."
        )
    if code == 500:
        return (
            "Erro interno do servidor — a loja está retornando erro 500 para os visitantes "
            "desta página. A causa é geralmente um bug no tema ou num aplicativo instalado."
        )
    if code in (401, 403):
        return (
            f"Acesso negado (HTTP {code}) — conteúdo que deveria ser público está "
            "bloqueado. Visitantes não logados veem um erro de permissão em vez da página."
        )
    if code >= 500:
        return (
            f"Erro de servidor (HTTP {code}) — a loja está falhando para os visitantes "
            "desta página. Pode ser sobrecarga, manutenção ou bug no servidor."
        )
    if code >= 400:
        return (
            f"Erro do cliente (HTTP {code}) — a requisição para esta URL está sendo "
            "rejeitada pelo servidor."
        )
    return f"Página retornou código HTTP {code} em vez de 200. {detail or ''}"


def _console_errors(check_id, check_name, detail, value, threshold, unit) -> str:
    count = int(value) if value else 0
    plural = "erros" if count > 1 else "erro"
    return (
        f"{count} {plural} de JavaScript detectado(s) no console do navegador. "
        "Scripts de terceiros (analytics, chat, personalização) ou código da própria loja "
        "falharam silenciosamente. O visitante não vê os erros, mas pode sentir as consequências: "
        "botão que não responde, preço que não carrega, carrinho que não abre, "
        "ou rastreamento de conversão quebrado."
    )


def _failed_requests(check_id, check_name, detail, value, threshold, unit) -> str:
    count = int(value) if value else 0
    plural = "requisições" if count > 1 else "requisição"
    vwo_present = detail and "visualwebsiteoptimizer" in (detail or "")
    analytics_note = ""
    if vwo_present:
        analytics_note = (
            " Há falhas no VWO (Visual Website Optimizer) — testes A/B e "
            "personalizações podem não estar sendo registradas corretamente."
        )
    return (
        f"{count} {plural} de rede com falha ao carregar esta página.{analytics_note} "
        "Falhas aqui afetam: rastreamento de conversões de anúncios (Meta, Google Ads), "
        "atribuição de campanhas, personalização e integrações de CRM. "
        "Se o script com falha for crítico (ex: checkout, pagamento), pode bloquear a compra."
    )


def _load_time(check_id, check_name, detail, value, threshold, unit) -> str:
    val_s = f"{value / 1000:.1f}s" if value else "?"
    lim_s = f"{threshold / 1000:.1f}s" if threshold else "?"
    return (
        f"A página demorou {val_s} para carregar completamente — {lim_s} é o limite. "
        "Pesquisas de e-commerce mostram que cada segundo extra de espera reduz "
        "conversões em ~7%. Em mobile, 53% dos visitantes abandonam páginas que "
        "demoram mais de 3 segundos. Visitantes vindos de anúncios pagos são ainda "
        "mais intolerantes."
    )


def _lcp(check_id, check_name, detail, value, threshold, unit) -> str:
    val_s = f"{value / 1000:.2f}s" if value else "?"
    lim_s = f"{threshold / 1000:.1f}s" if threshold else "?"
    return (
        f"O maior elemento visual da página (imagem principal, banner ou título) demorou "
        f"{val_s} para aparecer na tela — limite é {lim_s}. "
        "Durante este tempo a página parece vazia para o cliente. "
        "Google considera: ≤2.5s = bom, >4s = ruim. "
        "LCP lento prejudica o ranking de busca orgânica e o Quality Score de anúncios pagos."
    )


def _cls(check_id, check_name, detail, value, threshold, unit) -> str:
    val = f"{value:.3f}" if value else "?"
    lim = f"{threshold:.2f}" if threshold else "?"
    return (
        f"O layout da página se deslocou visualmente durante o carregamento (CLS = {val}, "
        f"limite = {lim}). Botões e links 'pulam' para outros lugares enquanto o cliente "
        "tenta clicar, causando cliques acidentais e frustração. "
        "Google penaliza CLS > 0.1 no ranking de busca e em anúncios pagos."
    )


def _fid(check_id, check_name, detail, value, threshold, unit) -> str:
    val_ms = f"{value:.0f}ms" if value else "?"
    lim_ms = f"{threshold:.0f}ms" if threshold else "?"
    return (
        f"A página ficou sem responder por {val_ms} enquanto carregava (limite = {lim_ms}). "
        "Se um cliente clicar em 'Adicionar ao Carrinho' ou qualquer botão nesse intervalo, "
        "não terá resposta — e provavelmente achará que o botão está quebrado e vai embora."
    )


def _popup_dispara(check_id, check_name, detail, value, threshold, unit) -> str:
    return (
        "O popup de captação de leads não apareceu após o tempo esperado. "
        "Isso significa que o formulário de e-mail não está sendo exibido para novos visitantes — "
        "perda direta de oportunidades de CRM, cupons de boas-vindas e recuperação de abandono."
    )


def _popup_botao_fechar(check_id, check_name, detail, value, threshold, unit) -> str:
    return (
        "O botão de fechar o popup não está visível. O visitante fica 'preso' sem "
        "conseguir dispensar o popup — bloqueia completamente a navegação e a compra. "
        "Esconder o close é crítico: segundo o playbook CRO, derruba a conversão da página."
    )


def _popup_fechar_funciona(check_id, check_name, detail, value, threshold, unit) -> str:
    return (
        "O clique no botão de fechar não funciona — o popup permanece na tela. "
        "O visitante está preso: não consegue acessar produtos, menus ou o carrinho. "
        "Equivale a um bloqueio total da loja para qualquer cliente que veja o popup."
    )


def _popup_scroll_block(check_id, check_name, detail, value, threshold, unit) -> str:
    return (
        "A página não aceita mais scroll após fechar o popup. O visitante não consegue "
        "rolar para ver produtos, categorias ou informações abaixo da dobra — "
        "como se a página tivesse travado. Afeta especialmente o mobile."
    )


def _popup_click_block(check_id, check_name, detail, value, threshold, unit) -> str:
    return (
        "Após fechar o popup, os cliques na página não funcionam. Há um overlay invisível "
        "bloqueando a interação. O visitante não consegue clicar em produtos, menus ou botões — "
        "perda total de navegabilidade da loja até a página ser recarregada."
    )


def _popup_loop(check_id, check_name, detail, value, threshold, unit) -> str:
    return (
        "O popup reapareceu na mesma sessão após ser fechado. Viola a regra de máximo "
        "1 exibição por sessão (24h). Isso cria uma experiência irritante que aumenta "
        "a taxa de rejeição e prejudica a percepção da marca."
    )


def _flow_or_popup_handler(check_id, check_name, detail, value, threshold, unit) -> str:
    # Popup check não mapeado
    if check_id.startswith("popup_"):
        return (
            f"Uma verificação do popup falhou: {detail or 'sem detalhe disponível'}. "
            "Popups com problemas técnicos podem bloquear a navegação e a compra."
        )

    # Fluxo funcional — extrair contexto do check_name
    if "→" in check_name:
        flow_name, step_name = check_name.split("→", 1)
        flow_name = flow_name.strip()
        step_name = step_name.strip()
    else:
        flow_name = "fluxo"
        step_name = check_name

    base = f"A etapa '{step_name}' do fluxo '{flow_name}' falhou durante a simulação automática."

    if detail:
        detail_lower = detail.lower()
        if "não encontrado" in detail_lower or "não visível" in detail_lower or "não clicável" in detail_lower:
            base += (
                " Um elemento da interface não foi localizado na tela — "
                "pode ter sido removido do tema, ter um seletor CSS desatualizado, "
                "ou simplesmente não estar visível nessa situação."
            )
        elif "timeout" in detail_lower or "navegação" in detail_lower:
            base += (
                " A página demorou mais que o esperado para responder — "
                "pode ser lentidão da loja, redirecionamento inesperado ou erro de servidor."
            )
        elif "url" in detail_lower:
            base += (
                " A URL após a ação não correspondeu ao esperado — "
                "possível redirecionamento inesperado ou alteração no fluxo da loja."
            )
        elif "preso" in detail_lower or "bloqueado" in detail_lower:
            base += (
                " O fluxo ficou bloqueado — um elemento está impedindo a continuação "
                "do processo de compra."
            )

    base += " Um cliente real tentando executar esta ação encontraria o mesmo problema."
    return base


# ── Tabela de despacho ────────────────────────────────────────────────────────

_HANDLERS = {
    "http_status": _http_status,
    "console_errors": _console_errors,
    "failed_requests": _failed_requests,
    "load_time": _load_time,
    "lcp": _lcp,
    "cls": _cls,
    "fid": _fid,
    "popup_dispara": _popup_dispara,
    "popup_botao_fechar": _popup_botao_fechar,
    "popup_fechar_funciona": _popup_fechar_funciona,
    "popup_scroll_block": _popup_scroll_block,
    "popup_click_block": _popup_click_block,
    "popup_loop": _popup_loop,
}
