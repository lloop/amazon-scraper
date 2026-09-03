const { Deck, OrbitView, ScatterplotLayer } = deck;

const tooltip = document.getElementById('tooltip');
const statusElem = document.getElementById('status');

const CATEGORY_COLORS = {
    'wireless headphones': [0, 255, 204],
    'mechanical keyboard': [255, 0, 127],
    'gaming mouse':       [255, 204, 0],
    '4k monitor':         [0, 153, 255]
};
const DEFAULT_COLOR = [220, 220, 220];

async function initVisualizer() {
    try {
        const response = await fetch('/api/products?valid_price_only=true');
        if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
        
        const result = await response.json();
        if (result.status !== 'success') throw new Error(result.message);
        
        const products = result.data;
        if (products.length === 0) {
            statusElem.innerText = "API connected, but database returned 0 valid records.";
            return;
        }

        statusElem.innerText = `Plotted ${products.length} product nodes in deck.gl.`;

        // Pass container div to `parent` ONLY
        new Deck({
            parent: document.getElementById('canvas-container'),
            views: new OrbitView({
                orbitAxis: 'Y',
                fov: 50
            }),
            initialViewState: {
                target: [0, 0, 0],
                zoom: 1.5,
                rotationX: 25,
                rotationOrbit: -35
            },
            controller: true,
            layers: [
                new ScatterplotLayer({
                    id: 'amazon-products-layer',
                    data: products,
                    
                    // Coordinate Mapping [X, Y, Z]
                    getPosition: d => [
                        (d.price - 50) * 0.3,                          // X: Price
                        ((d.rating || 3.0) - 3.0) * 15 - 10,           // Y: Rating
                        (Math.min(d.review_count || 0, 5000) / 100) - 25 // Z: Reviews
                    ],
                    
                    // Style
                    getFillColor: d => CATEGORY_COLORS[d.category] || DEFAULT_COLOR,
                    getRadius: 1.8,
                    radiusMinPixels: 4,
                    radiusMaxPixels: 15,
                    opacity: 0.85,
                    
                    // Hover & Pick logic
                    pickable: true,
                    onHover: info => handleHover(info)
                })
            ]
        });

    } catch (err) {
        console.error("deck.gl initialization failed:", err);
        statusElem.innerText = `Error: ${err.message}`;
    }
}

function handleHover(info) {
    if (info.object) {
        const item = info.object;
        tooltip.style.display = 'block';
        tooltip.style.left = `${info.x + 12}px`;
        tooltip.style.top = `${info.y + 12}px`;
        tooltip.innerHTML = `
            <strong>${item.title.substring(0, 40)}...</strong><br/>
            Category: <em>${item.category}</em><br/>
            Price: $${item.price} | Rating: ${item.rating}★<br/>
            Reviews: ${item.review_count || 0}
        `;
    } else {
        tooltip.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', initVisualizer);