from jinja2 import Template

def load_prompt(filename: str, customer: dict = None) -> str:
    filepath = f"src/prompts/{filename}"
    with open(filepath, "r", encoding="utf-8") as f:
        template_str = f.read()
    template = Template(template_str)
    if customer:
        return template.render(**customer)
    return template.render()
