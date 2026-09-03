let scene, camera, renderer, controls;
let productData = [];
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const tooltip = document.getElementById('tooltip');

const CATEGORY_COLORS = {
    'wireless headphones': 0x00ffcc,
    'mechanical keyboard': 0xff007f,
    'gaming mouse': 0xffcc00,
    '4k monitor': 0x0099ff
};

function initScene() {
    const container = document.getElementById('canvas-container');
    
    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050508, 0.005);

    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.set(50, 40, 80);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    container.appendChild(renderer.domElement);

    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Lights & Grid Grid
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
    scene.add(ambientLight);

    const gridHelper = new THREE.GridHelper(100, 20, 0x444444, 0x222222);
    gridHelper.position.y = -20;
    scene.add(gridHelper);

    window.addEventListener('resize', onWindowResize);
    window.addEventListener('mousemove', onMouseMove);

    animate();
}

async function loadAndPlotData() {
    try {
        const response = await fetch('/api/products?valid_price_only=true');
        const result = await response.json();
        
        if (result.status !== 'success') throw new Error(result.message);
        productData = result.data;

        document.getElementById('status').innerText = `Plotted ${productData.length} product nodes.`;

        // Plot Each Product Node
        const sphereGeo = new THREE.SphereGeometry(1.2, 16, 16);

        productData.forEach((item) => {
            const color = CATEGORY_COLORS[item.category] || 0xffffff;
            const material = new THREE.MeshStandardMaterial({
                color: color,
                roughness: 0.3,
                metalness: 0.2
            });

            const mesh = new THREE.Mesh(sphereGeo, material);

            // Coordinate mappings
            const x = (item.price - 50) * 0.3;                           // Price on X
            const y = ((item.rating || 3.0) - 3.0) * 15 - 10;             // Rating on Y
            const z = (Math.min(item.review_count || 0, 5000) / 100) - 25;  // Reviews on Z

            mesh.position.set(x, y, z);
            mesh.userData = item;

            scene.add(mesh);
        });

    } catch (err) {
        document.getElementById('status').innerText = `Error: ${err.message}`;
    }
}

function onMouseMove(event) {
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(scene.children);

    const nodeIntersects = intersects.filter(i => i.object.userData && i.object.userData.title);

    if (nodeIntersects.length > 0) {
        const item = nodeIntersects[0].object.userData;
        tooltip.style.display = 'block';
        tooltip.style.left = event.clientX + 10 + 'px';
        tooltip.style.top = event.clientY + 10 + 'px';
        tooltip.innerHTML = `<strong>${item.title.substring(0, 35)}...</strong><br/>` +
                            `Price: $${item.price} | Rating: ${item.rating}★`;
    } else {
        tooltip.style.display = 'none';
    }
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

// Initialize when script loads
initScene();
loadAndPlotData();