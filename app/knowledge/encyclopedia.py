import os
from typing import Dict, List, Optional
from app.knowledge.instruments import get_all_instruments, InstrumentInfo

# Mapowanie sektorów na ikony/emoji
SECTOR_ICONS = {
    "Finanse": "🏦",
    "Usługi Finansowe": "🏦",
    "Surowce": "⛏️",
    "Odzież": "👕",
    "Energetyka": "⚡",
    "Energia": "⚡",
    "Handel": "🛒",
    "Media": "📺",
    "Telekomunikacja": "📡",
    "IT": "💻",
    "Biotechnologia": "🧬",
    "Medyczne": "⚕️",
    "Transport": "🚂",
    "Gaming": "🎮",
    "Nieruchomości": "🏢",
    "Budownictwo": "🏗️",
    "AGD": "🧺", 
    "Indeks": "📈",
    "Paliwa": "⛽",
    "Ubezpieczenia": "🛡️",
    "Dobra podstawowe": "🧻",
    "Napoje": "🥤",
    "Gastronomia": "🍔",
    "Farmacja": "💊",
    "Górnictwo": "⛏️",
    "E-commerce": "📦",
    "Chemia": "⚗️",
    "Dobra luksusowe": "💎",
    "Technologia": "🤖",
    "Półprzewodniki": "💾",
    "Motoryzacja": "🚗",
    "Oprogramowanie": "💿",
    "Sieci": "🌐",
    "Waluty": "💱",
    "Crypto": "₿",
    "Agro": "🌾",
    "Rolnictwo": "🌾",
    "Metale Szlachetne": "🥇",
    "Obronność": "🛡️",
    "Cyberbezpieczeństwo": "🔒",
    "Obligacje": "📜",
    "Ochrona Zdrowia": "🏥",
    "Rozrywka": "🎢",
    "Lotnictwo": "✈️",
    "Przemysł": "🏭",
    "Użyteczność Publiczna": "💡",
    "Dobra Konsumpcyjne": "🛍️",
    "USA": "🇺🇸",
    "Europa": "🇪🇺",
    "Niemcy": "🇩🇪",
    "UK": "🇬🇧",
    "Japonia": "🇯🇵",
    "Chiny": "🇨🇳",
    "Rynki Wschodzące": "🌏",
    "Rynki Rozwinięte": "🌍",
    "USA Small Cap": "🇺🇸"
}

DEFAULT_ICON = "📊"

def get_icon_for_sector(sector: str) -> str:
    return SECTOR_ICONS.get(sector, DEFAULT_ICON)

def generate_encyclopedia_html(output_path: str = "encyclopedia.html"):
    """
    Generuje plik HTML z responsywną bazą wiedzy o instrumentach.
    """
    
    html_content = """
    <!DOCTYPE html>
    <html lang="pl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Encyklopedia Instrumentów Finansowych</title>
        <style>
            :root {
                --primary-color: #2c3e50;
                --accent-color: #3498db;
                --bg-color: #f4f7f6;
                --card-bg: #ffffff;
                --text-color: #333;
                --text-secondary: #7f8c8d;
                --section-header-bg: #e9ecef;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-color);
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }
            
            header {
                text-align: center;
                margin-bottom: 40px;
            }
            
            h1 {
                color: var(--primary-color);
                font-size: 2.5rem;
                margin-bottom: 10px;
            }
            
            .search-container {
                max-width: 600px;
                margin: 0 auto 40px;
                position: relative;
            }
            
            #search-input {
                width: 100%;
                padding: 15px 20px;
                font-size: 1.1rem;
                border: 2px solid #ddd;
                border-radius: 30px;
                outline: none;
                transition: border-color 0.3s;
                box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            }
            
            #search-input:focus {
                border-color: var(--accent-color);
            }
            
            .category-section {
                margin-bottom: 50px;
                animation: fadeIn 0.5s ease-in-out;
            }

            .section-header {
                font-size: 2rem;
                color: var(--primary-color);
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 3px solid var(--accent-color);
                display: flex;
                align-items: center;
            }

            .subsection-header {
                font-size: 1.5rem;
                color: var(--text-color);
                margin: 30px 0 20px;
                padding-left: 15px;
                border-left: 5px solid var(--accent-color);
                background-color: #fff;
                padding: 10px 15px;
                border-radius: 0 8px 8px 0;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            }
            
            .grid-container {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 25px;
                max-width: 1400px;
                margin: 0 auto;
            }
            
            .card {
                background-color: var(--card-bg);
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
                padding: 25px;
                transition: transform 0.3s, box-shadow 0.3s;
                display: flex;
                flex-direction: column;
                border-top: 5px solid transparent;
            }
            
            .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            }
            
            .card-header {
                display: flex;
                align-items: center;
                margin-bottom: 15px;
            }
            
            .icon {
                font-size: 2.5rem;
                margin-right: 15px;
                background: #f0f3f5;
                width: 60px;
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
            }
            
            .title-group {
                flex: 1;
            }
            
            .symbol {
                font-weight: bold;
                color: var(--accent-color);
                font-size: 0.9rem;
                display: block;
            }
            
            .name {
                font-weight: 700;
                font-size: 1.2rem;
                margin: 0;
                line-height: 1.2;
            }
            
            .badges {
                display: flex;
                gap: 8px;
                margin-bottom: 15px;
                flex-wrap: wrap;
            }
            
            .badge {
                font-size: 0.75rem;
                padding: 4px 10px;
                border-radius: 15px;
                background-color: #eee;
                color: #555;
                font-weight: 600;
            }
            
            .badge.sector {
                background-color: #e1f5fe;
                color: #0277bd;
            }
            
            .badge.type {
                background-color: #f3e5f5;
                color: #7b1fa2;
            }
            
            .description {
                color: var(--text-secondary);
                font-size: 0.95rem;
                margin-bottom: 20px;
                flex-grow: 1;
            }
            
            .expand-btn {
                margin-top: auto;
                background: none;
                border: none;
                color: var(--accent-color);
                cursor: pointer;
                font-weight: 600;
                padding: 0;
                text-align: left;
                font-size: 0.9rem;
            }
            
            .details {
                display: none;
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid #eee;
                font-size: 0.9rem;
            }
            
            .details.show {
                display: block;
                animation: fadeIn 0.5s;
            }
            
            .fact-sheet {
                background: #f8f9fa;
                padding: 10px;
                border-radius: 8px;
                margin-bottom: 15px;
            }
            
            .fact-sheet p {
                margin: 5px 0;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            ul {
                padding-left: 20px;
                margin: 5px 0;
            }
            
            h4 {
                margin: 15px 0 5px;
                color: var(--primary-color);
                font-size: 1rem;
            }
        </style>
    </head>
    <body>
        <header>
            <h1>📚 Encyklopedia Instrumentów</h1>
            <p>Kompleksowa baza wiedzy o rynkach finansowych</p>
        </header>
        
        <div class="search-container">
            <input type="text" id="search-input" placeholder="🔍 Szukaj instrumentu, sektora lub typu...">
        </div>
        
        <div id="content-area">
    """
    
    # Pobierz wszystkie instrumenty
    all_instruments = get_all_instruments()
    
    # Sortuj po nazwie
    all_instruments.sort(key=lambda x: x.name)
    
    # Grupowanie
    categories = {
        "Indeksy": [],
        "Surowce": [],
        "Kryptowaluty": [],
        "ETF / ETC": [],
        "Akcje": [], 
        "Inne": []
    }
    
    for info in all_instruments:
        atype = info.asset_type
        if not atype:
            categories["Inne"].append(info)
            continue
            
        if "Indeks" in atype:
            categories["Indeksy"].append(info)
        elif "Kryptowaluta" in atype:
            categories["Kryptowaluty"].append(info)
        elif "ETF" in atype or "ETN" in atype or "ETC" in atype:
            categories["ETF / ETC"].append(info)
        elif "Futures" in atype or "Surowiec" in atype:
            categories["Surowce"].append(info)
        elif "Akcja" in atype:
            categories["Akcje"].append(info)
        else:
            categories["Inne"].append(info)
            
    # Definicja kolejności wyświetlania
    display_order = ["Indeksy", "Surowce", "Kryptowaluty", "ETF / ETC", "Akcje", "Inne"]
    
    for cat_name in display_order:
        instruments = categories.get(cat_name, [])
        if not instruments:
            continue
            
        html_content += f"""
        <div class="category-section" id="section-{cat_name.replace(' ', '-').replace('/', '').lower()}">
            <h2 class="section-header">{cat_name}</h2>
        """
        
        # Specjalne traktowanie dla Akcji - podział na branże
        if cat_name == "Akcje":
            # Grupuj po sektorach
            sectors = {}
            for info in instruments:
                sec = info.sector or "Inne"
                # Mapowanie nazw sektorów na bardziej przyjazne (opcjonalnie)
                if sec == "Finanse":
                    sec = "Usługi Finansowe (Finanse)"
                
                if sec not in sectors:
                    sectors[sec] = []
                sectors[sec].append(info)
            
            # Sortuj sektory
            sorted_sectors = sorted(sectors.keys())
            
            for sec in sorted_sectors:
                sec_instruments = sectors[sec]
                html_content += f'<h3 class="subsection-header">{sec}</h3>'
                html_content += '<div class="grid-container">'
                
                for info in sec_instruments:
                    html_content += _generate_card_html(info)
                    
                html_content += '</div>'
        
        else:
            # Standardowy grid dla innych kategorii
            html_content += '<div class="grid-container">'
            for info in instruments:
                html_content += _generate_card_html(info)
            html_content += '</div>'
            
        html_content += "</div>"
    
    # Footer and Scripts
    html_content += """
        </div>
        
        <script>
            const searchInput = document.getElementById('search-input');
            const cards = document.querySelectorAll('.card');
            const sections = document.querySelectorAll('.category-section');
            
            searchInput.addEventListener('input', (e) => {
                const term = e.target.value.toLowerCase();
                
                cards.forEach(card => {
                    const searchData = card.getAttribute('data-search');
                    if (searchData.includes(term)) {
                        card.style.display = 'flex';
                    } else {
                        card.style.display = 'none';
                    }
                });
                
                // Ukrywanie pustych sekcji i podsekcji
                sections.forEach(section => {
                    let hasVisible = false;
                    section.querySelectorAll('.card').forEach(c => {
                         if (c.style.display !== 'none') hasVisible = true;
                    });
                    
                    if (hasVisible) {
                        section.style.display = 'block';
                    } else {
                        section.style.display = 'none';
                    }
                });
            });
            
            function toggleDetails(btn) {
                const details = btn.nextElementSibling;
                details.classList.toggle('show');
                if (details.classList.contains('show')) {
                    btn.textContent = 'Mniej informacji ▲';
                } else {
                    btn.textContent = 'Więcej informacji ▼';
                }
            }
        </script>
    </body>
    </html>
    """
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return output_path

def _generate_card_html(info: InstrumentInfo) -> str:
    symbol = info.symbol
    name = info.name
    sector = info.sector or "Inne"
    asset_type = info.asset_type or "Instrument"
    icon = get_icon_for_sector(sector)
    
    description = info.description
    history = info.history
    evolution = info.evolution
    key_features = info.key_features
    
    # New detailed fields
    founding_year = getattr(info, "founding_year", "Brak danych")
    company_size = getattr(info, "company_size", "Brak danych")
    products = getattr(info, "products", [])
    famous_for = getattr(info, "famous_for", "Brak danych")
    
    features_html = ""
    if key_features:
        features_html = "<ul>" + "".join([f"<li>{f}</li>" for f in key_features]) + "</ul>"
        
    products_html = ""
    if products:
        products_html = "<ul>" + "".join([f"<li>{p}</li>" for p in products]) + "</ul>"
    else:
        products_html = "<p>Brak danych o produktach.</p>"
        
    card_html = f"""
    <div class="card" data-search="{name.lower()} {symbol.lower()} {sector.lower()} {asset_type.lower()}">
        <div class="card-header">
            <div class="icon">{icon}</div>
            <div class="title-group">
                <span class="symbol">{symbol}</span>
                <h3 class="name">{name}</h3>
            </div>
        </div>
        
        <div class="badges">
            <span class="badge sector">{sector}</span>
            <span class="badge type">{asset_type}</span>
        </div>
        
        <div class="description">
            {description}
        </div>
    
        <button class="expand-btn" onclick="toggleDetails(this)">Więcej informacji ▼</button>
        <div class="details">
            <div class="fact-sheet">
                <p><strong>📅 Rok założenia:</strong> {founding_year}</p>
                <p><strong>🏢 Wielkość:</strong> {company_size}</p>
                <p><strong>🌟 Znany z:</strong> {famous_for}</p>
            </div>
            
            <h4>📦 Produkty / Usługi</h4>
            {products_html}
        
            <h4>📜 Historia</h4>
            <p>{history}</p>
            
            <h4>📈 Ewolucja</h4>
            <p>{evolution}</p>
            
            <h4>🔑 Kluczowe cechy</h4>
            {features_html}
        </div>
    </div>
    """
    return card_html

if __name__ == "__main__":
    print("Generowanie Encyklopedii...")
    output = generate_encyclopedia_html()
    print(f"Gotowe! Utworzono plik: {output}")
