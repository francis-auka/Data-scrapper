from bs4 import BeautifulSoup

with open("jumia_debug.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

products = soup.select("article.prd")

with open("product_structure.txt", "w", encoding="utf-8") as f:
    if products:
        p = products[0]
        f.write(p.prettify())
        f.write("\n\n--- Analysis ---\n")
        
        name = p.select_one(".name")
        f.write(f"Title (.name): {name.get_text(strip=True) if name else 'Not Found'}\n")
        
        prc = p.select_one(".prc")
        f.write(f"Price (.prc): {prc.get_text(strip=True) if prc else 'Not Found'}\n")
        
        img = p.select_one("img")
        if img:
            f.write(f"Image src: {img.get('src')}\n")
            f.write(f"Image data-src: {img.get('data-src')}\n")
            f.write(f"Image class: {img.get('class')}\n")
    else:
        f.write("No products found")
