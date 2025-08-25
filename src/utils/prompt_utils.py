from jinja2 import Template

def load_prompt(filename: str, customer) -> str:
    filepath = f"src/prompts/{filename}"
    with open(filepath, "r", encoding="utf-8") as f:
        template_str = f.read()
    template = Template(template_str)

    return template.render(
        ten=customer.ten,
        gioi_tinh=customer.gioi_tinh,
        so_hop_dong=customer.so_hop_dong,
        khoan_vay=customer.khoan_vay,
        tien_thanh_toan=customer.tien_thanh_toan,
        han_thanh_toan=customer.han_thanh_toan,
        trang_thai=customer.trang_thai,
        prefix=customer.prefix,
    )
