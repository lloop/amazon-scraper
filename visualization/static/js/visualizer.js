const tooltip = document.getElementById('tooltip');
const statusElem = document.getElementById('status');
const filterContainer = document.getElementById('filter-container');

const CATEGORY_COLORS = {
    'wireless headphones': '#00ffcc',
    'mechanical keyboard': '#ff007f',
    'gaming mouse':       '#ffcc00',
    '4k monitor':         '#0099ff'
};
const DEFAULT_COLOR = '#dcdcdc';

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

        // statusElem.innerText = `Plotted ${products.length} product nodes in D3.js.`;

        // Layout Dimensions (Increased margins and row spacing)
        const categories = Array.from(new Set(products.map(p => p.category)));
        const rowHeight = 180;
        const margin = { top: 60, right: 120, bottom: 80, left: 220 };
        const width = 1200 - margin.left - margin.right;
        const height = (categories.length * rowHeight) - margin.top - margin.bottom;

        // Reset Containers
        d3.select("#chart").html("");
        filterContainer.innerHTML = "";

        const svg = d3.select("#chart")
            .append("svg")
            .attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);

        // Scales - Added 15% padding above max price to prevent right overflow
        const maxPrice = d3.max(products, d => d.price) || 200;
        const xScale = d3.scaleLinear()
            .domain([0, maxPrice * 1.15])
            .range([0, width]);

        const yScale = d3.scalePoint()
            .domain(categories)
            .range([0, height])
            .padding(0.8);

        const rawMaxReviews = d3.max(products, d => d.review_count || 0) || 1;
        const radiusScale = d3.scaleSqrt()
            .domain([0, rawMaxReviews])
            .range([5, 20]);

        // Axes & Grid
        const xAxis = d3.axisBottom(xScale).tickFormat(d => `$${d}`).ticks(10);
        
        svg.append("g")
            .attr("class", "axis")
            .attr("transform", `translate(0,${height + 35})`)
            .call(xAxis);

        svg.append("g")
            .attr("class", "grid")
            .attr("transform", `translate(0,${height + 35})`)
            .call(d3.axisBottom(xScale).ticks(10).tickSize(-height - 60).tickFormat(""));

        // Category Row Labels
        categories.forEach(cat => {
            svg.append("text")
                .attr("class", `category-label label-${cat.replace(/\s+/g, '-')}`)
                .attr("x", -25)
                .attr("y", yScale(cat))
                .attr("text-anchor", "end")
                .attr("dominant-baseline", "middle")
                .attr("fill", CATEGORY_COLORS[cat] || "#fff")
                .style("font-size", "14px")
                .style("font-weight", "700")
                .style("text-transform", "capitalize")
                .text(cat);
        });

        // D3 Physics Simulation with stronger Y-pull to prevent vertical bleeding
        const simulation = d3.forceSimulation(products)
            .force("x", d3.forceX(d => xScale(d.price)).strength(0.9))
            .force("y", d3.forceY(d => yScale(d.category)).strength(0.4))
            .force("collide", d3.forceCollide(d => radiusScale(d.review_count || 0) + 2))
            .stop();

        for (let i = 0; i < 180; ++i) simulation.tick();

        // Render Product Nodes
        const nodes = svg.append("g")
            .selectAll("circle")
            .data(products)
            .enter()
            .append("circle")
            .attr("class", d => `node-circle cat-${d.category.replace(/\s+/g, '-')}`)
            .attr("cx", d => Math.min(width - 10, Math.max(10, d.x))) // Bound X within frame
            .attr("cy", d => d.y)
            .attr("r", d => radiusScale(d.review_count || 0))
            .attr("fill", d => CATEGORY_COLORS[d.category] || DEFAULT_COLOR)
            .attr("fill-opacity", 0.75)
            .attr("stroke", d => CATEGORY_COLORS[d.category] || DEFAULT_COLOR)
            .attr("stroke-width", 1.5)
            .style("cursor", "pointer");

        // Hover Handlers
        nodes
            .on("mouseover", (event, d) => {
                d3.select(event.currentTarget)
                    .attr("fill-opacity", 1)
                    .attr("stroke", "#ffffff");

                tooltip.style.display = 'block';
                tooltip.innerHTML = `
                    <strong>${d.title.substring(0, 50)}...</strong><br/>
                    Category: <em>${d.category}</em><br/>
                    Price: $${d.price} | Rating: ${d.rating || 'N/A'}★<br/>
                    Reviews: ${d.review_count || 0}
                `;
            })
            .on("mousemove", (event) => {
                tooltip.style.left = `${event.pageX + 15}px`;
                tooltip.style.top = `${event.pageY + 15}px`;
            })
            .on("mouseout", (event, d) => {
                d3.select(event.currentTarget)
                    .attr("fill-opacity", 0.75)
                    .attr("stroke", CATEGORY_COLORS[d.category] || DEFAULT_COLOR);

                tooltip.style.display = 'none';
            });

        // Build Category Isolation Buttons
        buildCategoryFilterButtons(['All', ...categories]);

    } catch (err) {
        console.error("D3 initialization failed:", err);
        statusElem.innerText = `Error: ${err.message}`;
    }
}

function buildCategoryFilterButtons(categories) {
    categories.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = `filter-btn ${cat === 'All' ? 'active' : ''}`;
        btn.innerText = cat.toUpperCase();

        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const selectedCatClass = cat === 'All' ? 'All' : cat.replace(/\s+/g, '-');

            if (selectedCatClass === 'All') {
                d3.selectAll('.node-circle').transition().duration(300).style('opacity', 1).style('pointer-events', 'auto');
                d3.selectAll('.category-label').transition().duration(300).style('opacity', 1);
            } else {
                d3.selectAll('.node-circle').each(function() {
                    const circle = d3.select(this);
                    if (circle.classed(`cat-${selectedCatClass}`)) {
                        circle.transition().duration(300).style('opacity', 1).style('pointer-events', 'auto');
                    } else {
                        circle.transition().duration(300).style('opacity', 0.08).style('pointer-events', 'none');
                    }
                });

                d3.selectAll('.category-label').each(function() {
                    const label = d3.select(this);
                    if (label.classed(`label-${selectedCatClass}`)) {
                        label.transition().duration(300).style('opacity', 1);
                    } else {
                        label.transition().duration(300).style('opacity', 0.25);
                    }
                });
            }
        });

        filterContainer.appendChild(btn);
    });
}

document.addEventListener('DOMContentLoaded', initVisualizer);