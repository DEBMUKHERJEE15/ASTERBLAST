import * as THREE from 'three';
import { OrbitControls } from 'jsm/controls/OrbitControls.js';

// Scene setup
let scene, camera, renderer, controls;
let planets = [];
let asteroids = [];
let stars = [];
let sun, sunGlow;
let autoRotate = true;
let showOrbits = true;

// Initialize
init();
animate();

function init() {
    // Scene
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x000000);
    scene.fog = new THREE.FogExp2(0x000000, 0.00015);

    // Camera
    camera = new THREE.PerspectiveCamera(
        60,
        window.innerWidth / window.innerHeight,
        0.1,
        1000
    );
    camera.position.set(0, 40, 70);

    // Renderer
    const canvas = document.getElementById('three-canvas');
    renderer = new THREE.WebGLRenderer({ 
        canvas,
        antialias: true,
        alpha: true 
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;

    // Controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.enableZoom = true;
    controls.enablePan = false;
    controls.minDistance = 20;
    controls.maxDistance = 200;
    controls.autoRotate = autoRotate;
    controls.autoRotateSpeed = 0.3;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.2);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0xffffff, 2, 300);
    pointLight.position.set(0, 0, 0);
    pointLight.castShadow = true;
    pointLight.shadow.mapSize.width = 2048;
    pointLight.shadow.mapSize.height = 2048;
    scene.add(pointLight);

    // Create starfield
    createStarfield();

    // Create Sun
    createSun();

    // Create planets
    createPlanet(6, 0xc4c4c4, 10, 0.008, 'Mercury');
    createPlanet(8, 0xe5e5e5, 15, 0.006, 'Venus');
    createPlanet(8.5, 0xd4d4d4, 20, 0.005, 'Earth');
    createPlanet(7, 0xcccccc, 26, 0.004, 'Mars');
    createPlanet(15, 0xe8e8e8, 45, 0.002, 'Jupiter');
    createPlanet(13, 0xf0f0f0, 60, 0.0015, 'Saturn');

    // Create asteroid belt
    createAsteroidBelt();

    // Event listeners
    window.addEventListener('resize', onWindowResize);
    document.getElementById('rotateBtn').addEventListener('click', toggleRotation);
    document.getElementById('resetBtn').addEventListener('click', resetCamera);
    document.getElementById('orbitsBtn').addEventListener('click', toggleOrbitsDisplay);

    // Hide loading screen
    setTimeout(() => {
        document.getElementById('loading').classList.add('hidden');
    }, 1500);
}

function createStarfield() {
    const starsGeometry = new THREE.BufferGeometry();
    const starsMaterial = new THREE.PointsMaterial({
        color: 0xffffff,
        size: 0.5,
        transparent: true,
        opacity: 0.8
    });

    const starsVertices = [];
    for (let i = 0; i < 3000; i++) {
        const x = (Math.random() - 0.5) * 400;
        const y = (Math.random() - 0.5) * 400;
        const z = (Math.random() - 0.5) * 400;
        starsVertices.push(x, y, z);
    }

    starsGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starsVertices, 3));
    const starField = new THREE.Points(starsGeometry, starsMaterial);
    scene.add(starField);
}

function createSun() {
    // Main sun
    const sunGeometry = new THREE.SphereGeometry(5, 64, 64);
    const sunMaterial = new THREE.MeshBasicMaterial({
        color: 0xffffff,
        emissive: 0xffffff,
        emissiveIntensity: 1
    });
    sun = new THREE.Mesh(sunGeometry, sunMaterial);
    sun.castShadow = false;
    sun.receiveShadow = false;
    scene.add(sun);

    // Sun glow
    const glowGeometry = new THREE.SphereGeometry(6, 32, 32);
    const glowMaterial = new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.15,
        side: THREE.BackSide
    });
    sunGlow = new THREE.Mesh(glowGeometry, glowMaterial);
    scene.add(sunGlow);

    // Additional glow layers
    for (let i = 1; i <= 3; i++) {
        const glowSize = 6 + i * 1.5;
        const glowOpacity = 0.1 / i;
        const extraGlowGeometry = new THREE.SphereGeometry(glowSize, 32, 32);
        const extraGlowMaterial = new THREE.MeshBasicMaterial({
            color: 0xffffff,
            transparent: true,
            opacity: glowOpacity,
            side: THREE.BackSide
        });
        const extraGlow = new THREE.Mesh(extraGlowGeometry, extraGlowMaterial);
        scene.add(extraGlow);
    }
}

function createPlanet(size, color, distance, speed, name) {
    // Planet mesh
    const geometry = new THREE.SphereGeometry(size / 10, 32, 32);
    const material = new THREE.MeshStandardMaterial({
        color: color,
        metalness: 0.3,
        roughness: 0.7,
        emissive: color,
        emissiveIntensity: 0.05
    });
    const planet = new THREE.Mesh(geometry, material);
    planet.castShadow = true;
    planet.receiveShadow = true;
    planet.position.x = distance;

    // Orbit group
    const orbit = new THREE.Group();
    orbit.add(planet);

    // Orbit line
    if (showOrbits) {
        const orbitCurve = new THREE.EllipseCurve(
            0, 0,
            distance, distance,
            0, 2 * Math.PI,
            false,
            0
        );
        const points = orbitCurve.getPoints(100);
        const orbitGeometry = new THREE.BufferGeometry().setFromPoints(points);
        const orbitMaterial = new THREE.LineBasicMaterial({
            color: 0x333333,
            transparent: true,
            opacity: 0.3
        });
        const orbitLine = new THREE.Line(orbitGeometry, orbitMaterial);
        orbitLine.rotation.x = Math.PI / 2;
        orbit.add(orbitLine);
    }

    scene.add(orbit);
    planets.push({
        orbit: orbit,
        planet: planet,
        distance: distance,
        speed: speed,
        name: name
    });
}

function createAsteroidBelt() {
    const asteroidCount = 300;
    const innerRadius = 32;
    const outerRadius = 40;

    for (let i = 0; i < asteroidCount; i++) {
        // Random position in belt
        const angle = Math.random() * Math.PI * 2;
        const radius = innerRadius + Math.random() * (outerRadius - innerRadius);
        
        // Create asteroid
        const size = Math.random() * 0.15 + 0.05;
        const geometry = new THREE.DodecahedronGeometry(size, 0);
        const material = new THREE.MeshStandardMaterial({
            color: 0x888888,
            metalness: 0.5,
            roughness: 0.8,
            emissive: 0x222222,
            emissiveIntensity: 0.1
        });
        
        const asteroid = new THREE.Mesh(geometry, material);
        asteroid.position.x = Math.cos(angle) * radius;
        asteroid.position.z = Math.sin(angle) * radius;
        asteroid.position.y = (Math.random() - 0.5) * 3;
        
        asteroid.rotation.x = Math.random() * Math.PI;
        asteroid.rotation.y = Math.random() * Math.PI;
        asteroid.rotation.z = Math.random() * Math.PI;
        
        asteroid.castShadow = true;
        asteroid.receiveShadow = true;
        
        scene.add(asteroid);
        asteroids.push({
            mesh: asteroid,
            rotationSpeed: {
                x: (Math.random() - 0.5) * 0.02,
                y: (Math.random() - 0.5) * 0.02,
                z: (Math.random() - 0.5) * 0.02
            },
            orbitSpeed: 0.001 + Math.random() * 0.002,
            angle: angle,
            radius: radius
        });
    }
}

function animate() {
    requestAnimationFrame(animate);

    // Rotate sun
    if (sun) {
        sun.rotation.y += 0.001;
    }

    // Update planets
    planets.forEach(p => {
        p.orbit.rotation.y += p.speed;
        p.planet.rotation.y += 0.01;
    });

    // Update asteroids
    asteroids.forEach(a => {
        a.mesh.rotation.x += a.rotationSpeed.x;
        a.mesh.rotation.y += a.rotationSpeed.y;
        a.mesh.rotation.z += a.rotationSpeed.z;
        
        // Orbit around sun
        a.angle += a.orbitSpeed;
        a.mesh.position.x = Math.cos(a.angle) * a.radius;
        a.mesh.position.z = Math.sin(a.angle) * a.radius;
    });

    // Update controls
    controls.update();

    // Render
    renderer.render(scene, camera);
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function toggleRotation() {
    autoRotate = !autoRotate;
    controls.autoRotate = autoRotate;
}

function resetCamera() {
    camera.position.set(0, 40, 70);
    camera.lookAt(0, 0, 0);
    controls.target.set(0, 0, 0);
    controls.update();
}

function toggleOrbitsDisplay() {
    showOrbits = !showOrbits;
    
    // Remove all current planets
    planets.forEach(p => {
        scene.remove(p.orbit);
    });
    planets = [];
    
    // Recreate planets with new orbit visibility
    createPlanet(6, 0xc4c4c4, 10, 0.008, 'Mercury');
    createPlanet(8, 0xe5e5e5, 15, 0.006, 'Venus');
    createPlanet(8.5, 0xd4d4d4, 20, 0.005, 'Earth');
    createPlanet(7, 0xcccccc, 26, 0.004, 'Mars');
    createPlanet(15, 0xe8e8e8, 45, 0.002, 'Jupiter');
    createPlanet(13, 0xf0f0f0, 60, 0.0015, 'Saturn');
}

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth' });
        }
    });
});

// Filter buttons
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
    });
});

// CTA button
document.querySelector('.cta-button').addEventListener('click', function() {
    document.querySelector('#data').scrollIntoView({ behavior: 'smooth' });
});