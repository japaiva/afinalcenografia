from django import template

register = template.Library()

@register.filter
def moeda_brasileira(valor):
    try:
        valor = float(valor)
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

@register.filter
def duration_format(value):
    """
    Formata um timedelta como 'Xh Ymin'.
    Se não for um timedelta, retorna o valor como string.
    """
    if not value:
        return "-"
    try:
        total_seconds = int(value.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{hours}h {minutes}min"
    except Exception:
        return str(value)