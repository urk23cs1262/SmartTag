let socket = null;
let cameraStream = null;
let isProcessing = false;
let processingInterval = null;
let currentFPS = 0;
let frameCount = 0;
let lastFrameTime = performance.now();
let detectionHistory = [];
let charts = {};

document.addEventListener('DOMContentLoaded', function() {
    initializeAOS();
    initializePreloader();
    initializeNavbar();
    initializeTheme();
    initializeSocket();
    initializeEventListeners();
    initializeParticles();
    initializeTypewriter();
    initializeCounterAnimation();
    
    if (window.location.pathname.includes('dashboard.html')) {
        initializeDashboard();
    }
});

function initializeAOS() {
    AOS.init({
        duration: 1000,
        once: true,
        offset: 100,
        easing: 'ease-in-out'
    });
}

function initializePreloader() {
    window.addEventListener('load', function() {
        setTimeout(function() {
            document.getElementById('preloader').classList.add('hidden');
        }, 2000);
    });
}

function initializeNavbar() {
    const navbar = document.querySelector('.navbar');
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navMenu = document.getElementById('navMenu');
    
    window.addEventListener('scroll', function() {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });
    
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', function() {
            navMenu.classList.toggle('active');
            const icon = this.querySelector('i');
            if (navMenu.classList.contains('active')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    }
    
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.addEventListener('click', function() {
            navMenu.classList.remove('active');
            const icon = mobileMenuBtn?.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        });
    });
}

function initializeTheme() {
    const themeToggle = document.getElementById('themeToggle');
    if (!themeToggle) return;
    
    const icon = themeToggle.querySelector('i');
    
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-theme');
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
    }
    
    themeToggle.addEventListener('click', function() {
        document.body.classList.toggle('dark-theme');
        
        if (document.body.classList.contains('dark-theme')) {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
            localStorage.setItem('theme', 'dark');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
            localStorage.setItem('theme', 'light');
        }
    });
}

function initializeParticles() {
    const particlesContainer = document.getElementById('particles');
    if (!particlesContainer) return;
    
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.style.cssText = `
            position: absolute;
            width: ${Math.random() * 5 + 2}px;
            height: ${Math.random() * 5 + 2}px;
            background: var(--primary-color);
            border-radius: 50%;
            left: ${Math.random() * 100}%;
            top: ${Math.random() * 100}%;
            opacity: ${Math.random() * 0.5 + 0.2};
            animation: float ${Math.random() * 10 + 10}s linear infinite;
            animation-delay: ${Math.random() * 5}s;
        `;
        particlesContainer.appendChild(particle);
    }
}

function initializeTypewriter() {
    const typewriterElement = document.getElementById('typewriter');
    if (!typewriterElement) return;
    
    const phrases = [
        'AI-Powered Toll Verification',
        'Real-Time Fraud Detection',
        'Smart Traffic Management',
        'Intelligent FASTag System'
    ];
    
    let phraseIndex = 0;
    let charIndex = 0;
    let isDeleting = false;
    
    function type() {
        const currentPhrase = phrases[phraseIndex];
        
        if (isDeleting) {
            typewriterElement.textContent = currentPhrase.substring(0, charIndex - 1);
            charIndex--;
        } else {
            typewriterElement.textContent = currentPhrase.substring(0, charIndex + 1);
            charIndex++;
        }
        
        if (!isDeleting && charIndex === currentPhrase.length) {
            isDeleting = true;
            setTimeout(type, 2000);
        } else if (isDeleting && charIndex === 0) {
            isDeleting = false;
            phraseIndex = (phraseIndex + 1) % phrases.length;
            setTimeout(type, 500);
        } else {
            setTimeout(type, isDeleting ? 50 : 100);
        }
    }
    
    type();
}

function initializeCounterAnimation() {
    const counters = document.querySelectorAll('.stat-number');
    
    counters.forEach(counter => {
        const target = parseFloat(counter.getAttribute('data-target'));
        const updateCounter = () => {
            const current = parseFloat(counter.innerText);
            const increment = target / 50;
            
            if (current < target) {
                counter.innerText = Math.ceil(current + increment);
                setTimeout(updateCounter, 20);
            } else {
                counter.innerText = target;
            }
        };
        
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    updateCounter();
                    observer.unobserve(entry.target);
                }
            });
        });
        
        observer.observe(counter);
    });
}

function initializeSocket() {
    socket = io('http://localhost:5000', {
        transports: ['websocket'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5
    });
    
    socket.on('connect', function() {
        console.log('Connected to SmartTag server');
        updateConnectionStatus(true);
        showNotification('Connected to server', 'success');
    });
    
    socket.on('connect_error', function(error) {
        console.error('Connection error:', error);
        updateConnectionStatus(false);
        showNotification('Failed to connect to server', 'error');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateConnectionStatus(false);
        showNotification('Disconnected from server', 'warning');
    });
    
    socket.on('processed_frame', function(data) {
        updateUI(data);
        updateFPS();
    });
}

function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('connectionStatus');
    if (statusElement) {
        statusElement.textContent = connected ? 'Connected' : 'Disconnected';
        statusElement.style.color = connected ? 'var(--success-color)' : 'var(--danger-color)';
    }
}

function updateFPS() {
    frameCount++;
    const now = performance.now();
    const delta = now - lastFrameTime;
    
    if (delta >= 1000) {
        currentFPS = Math.round((frameCount * 1000) / delta);
        const fpsElement = document.getElementById('fps');
        if (fpsElement) fpsElement.textContent = currentFPS;
        frameCount = 0;
        lastFrameTime = now;
    }
}

function initializeEventListeners() {
    const startCameraBtn = document.getElementById('startCamera');
    const stopCameraBtn = document.getElementById('stopCamera');
    const uploadVideoBtn = document.getElementById('uploadVideo');
    const videoUpload = document.getElementById('videoUpload');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const clearResultsBtn = document.getElementById('clearResults');
    const exportResultsBtn = document.getElementById('exportResults');
    const backToTopBtn = document.getElementById('backToTop');
    
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            tabBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            const tab = this.getAttribute('data-tab');
            switchTab(tab);
        });
    });
    
    const tabLinks = document.querySelectorAll('.tab-link');
    tabLinks.forEach(link => {
        link.addEventListener('click', function() {
            tabLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            const tab = this.getAttribute('data-tab');
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById(tab + 'Tab').classList.add('active');
        });
    });
    
    if (startCameraBtn) {
        startCameraBtn.addEventListener('click', startCamera);
    }
    
    if (stopCameraBtn) {
        stopCameraBtn.addEventListener('click', stopCamera);
    }
    
    if (uploadVideoBtn) {
        uploadVideoBtn.addEventListener('click', () => videoUpload.click());
    }
    
    if (videoUpload) {
        videoUpload.addEventListener('change', uploadVideo);
    }
    
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', toggleFullscreen);
    }
    
    if (clearResultsBtn) {
        clearResultsBtn.addEventListener('click', clearResults);
    }
    
    if (exportResultsBtn) {
        exportResultsBtn.addEventListener('click', exportResults);
    }
    
    const contactForm = document.getElementById('contactForm');
    if (contactForm) {
        contactForm.addEventListener('submit', handleContactSubmit);
    }
    
    const watchDemoBtn = document.getElementById('watchDemo');
    if (watchDemoBtn) {
        watchDemoBtn.addEventListener('click', () => {
            document.getElementById('demo').scrollIntoView({ behavior: 'smooth' });
            setTimeout(() => {
                startCamera();
            }, 1000);
        });
    }
    
    window.addEventListener('scroll', function() {
        if (backToTopBtn) {
            if (window.scrollY > 500) {
                backToTopBtn.classList.add('show');
            } else {
                backToTopBtn.classList.remove('show');
            }
        }
    });
    
    if (backToTopBtn) {
        backToTopBtn.addEventListener('click', function() {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }
    
    const refreshData = document.getElementById('refreshData');
    if (refreshData) {
        refreshData.addEventListener('click', function() {
            loadDashboardData();
            showNotification('Dashboard data refreshed', 'success');
        });
    }
    
    const exportData = document.getElementById('exportData');
    if (exportData) {
        exportData.addEventListener('click', exportDashboardData);
    }
    
    const refreshTransactions = document.getElementById('refreshTransactions');
    if (refreshTransactions) {
        refreshTransactions.addEventListener('click', loadSampleTransactions);
    }
}

function switchTab(tab) {
    const videoFeed = document.getElementById('videoFeed');
    const uploadPlaceholder = document.getElementById('uploadPlaceholder');
    const startCameraBtn = document.getElementById('startCamera');
    const stopCameraBtn = document.getElementById('stopCamera');
    
    if (tab === 'camera') {
        videoFeed.style.display = 'block';
        uploadPlaceholder.style.display = 'none';
        startCameraBtn.disabled = false;
        stopCameraBtn.disabled = true;
        stopCamera();
    } else if (tab === 'upload') {
        videoFeed.style.display = 'none';
        uploadPlaceholder.style.display = 'flex';
        stopCamera();
    } else if (tab === 'sample') {
        videoFeed.style.display = 'block';
        videoFeed.src = 'https://via.placeholder.com/640x360/1a1b2f/4361ee?text=Sample+Footage';
        uploadPlaceholder.style.display = 'none';
        startCameraBtn.disabled = true;
        stopCameraBtn.disabled = false;
    }
}

async function startCamera() {
    try {
        cameraStream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment'
            } 
        });
        
        const videoElement = document.createElement('video');
        videoElement.srcObject = cameraStream;
        videoElement.play();
        
        document.getElementById('startCamera').disabled = true;
        document.getElementById('stopCamera').disabled = false;
        document.getElementById('videoFeed').src = '';
        
        isProcessing = true;
        processCameraFrames(videoElement);
        
        showNotification('Camera started successfully', 'success');
        
    } catch (error) {
        console.error('Error accessing camera:', error);
        showNotification('Could not access camera. Please check permissions.', 'error');
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }
    
    isProcessing = false;
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
    
    const startBtn = document.getElementById('startCamera');
    const stopBtn = document.getElementById('stopCamera');
    if (startBtn) startBtn.disabled = false;
    if (stopBtn) stopBtn.disabled = true;
    
    const videoFeed = document.getElementById('videoFeed');
    if (videoFeed) videoFeed.src = '';
    
    showNotification('Camera stopped', 'info');
}

function processCameraFrames(videoElement) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    
    processingInterval = setInterval(() => {
        if (!isProcessing || !videoElement.videoWidth) return;
        
        const maxWidth = 640;
        const scale = maxWidth / videoElement.videoWidth;
        canvas.width = maxWidth;
        canvas.height = videoElement.videoHeight * scale;
        
        context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        const imageData = canvas.toDataURL('image/jpeg', 0.8);
        
        if (socket && socket.connected) {
            const startTime = performance.now();
            socket.emit('stream_frame', { image: imageData });
            
            socket.once('processed_frame', () => {
                const processingTime = Math.round(performance.now() - startTime);
                const timeElement = document.getElementById('processingTime');
                if (timeElement) timeElement.textContent = processingTime + 'ms';
            });
        }
    }, 200);
}

async function uploadVideo(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.type.startsWith('video/')) {
        showNotification('Please select a video file', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('video', file);
    
    showLoading(true);
    
    try {
        const uploadResponse = await fetch('http://localhost:5000/api/upload_video', {
            method: 'POST',
            body: formData
        });
        
        const uploadData = await uploadResponse.json();
        
        if (uploadData.success) {
            showNotification('Video uploaded successfully', 'success');
            processVideoFile(file);
        }
    } catch (error) {
        console.error('Error uploading video:', error);
        showNotification('Error uploading video', 'error');
    } finally {
        showLoading(false);
    }
}

function processVideoFile(file) {
    const video = document.createElement('video');
    video.preload = 'metadata';
    
    video.onloadedmetadata = function() {
        URL.revokeObjectURL(video.src);
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL('image/jpeg');
        
        if (socket && socket.connected) {
            socket.emit('stream_frame', { image: imageData });
        }
    };
    
    video.src = URL.createObjectURL(file);
}

function toggleFullscreen() {
    const videoFeed = document.querySelector('.video-feed');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    
    if (!document.fullscreenElement) {
        videoFeed.requestFullscreen();
        if (fullscreenBtn) fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i>';
    } else {
        document.exitFullscreen();
        if (fullscreenBtn) fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>';
    }
}

function clearResults() {
    const vehicleList = document.getElementById('vehicleList');
    const fraudList = document.getElementById('fraudList');
    
    if (vehicleList) {
        vehicleList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-car"></i>
                <p>No vehicles detected</p>
            </div>
        `;
    }
    
    if (fraudList) {
        fraudList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-check-circle"></i>
                <p>No fraud detected</p>
            </div>
        `;
    }
    
    const vehicleCount = document.getElementById('vehicleCount');
    const plateCount = document.getElementById('plateCount');
    const fraudCount = document.getElementById('fraudCount');
    
    if (vehicleCount) vehicleCount.textContent = '0';
    if (plateCount) plateCount.textContent = '0';
    if (fraudCount) fraudCount.textContent = '0';
    
    detectionHistory = [];
    updateTimeline();
    
    showNotification('Results cleared', 'info');
}

function exportResults() {
    const results = {
        timestamp: new Date().toISOString(),
        stats: {
            vehicles: document.getElementById('vehicleCount')?.textContent || '0',
            plates: document.getElementById('plateCount')?.textContent || '0',
            frauds: document.getElementById('fraudCount')?.textContent || '0'
        },
        history: detectionHistory
    };
    
    const dataStr = JSON.stringify(results, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `smarttag-export-${Date.now()}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    showNotification('Results exported successfully', 'success');
}

function updateUI(data) {
    const videoFeed = document.getElementById('videoFeed');
    if (videoFeed && data.annotated_image) {
        videoFeed.src = data.annotated_image;
    }
    
    if (data.stats) {
        const vehicleCount = document.getElementById('vehicleCount');
        const plateCount = document.getElementById('plateCount');
        const fraudCount = document.getElementById('fraudCount');
        
        if (vehicleCount) vehicleCount.textContent = data.stats.vehicle_count || 0;
        if (plateCount) plateCount.textContent = data.stats.plate_count || 0;
        if (fraudCount) fraudCount.textContent = data.stats.fraud_count || 0;
    }
    
    const vehicleList = document.getElementById('vehicleList');
    if (vehicleList) {
        vehicleList.innerHTML = '';
        
        if (data.vehicles && data.vehicles.length > 0) {
            data.vehicles.forEach((vehicle, index) => {
                const item = document.createElement('div');
                item.className = 'list-item';
                
                const plateText = data.plates && data.plates[index] ? data.plates[index].text : 'N/A';
                const confidence = (vehicle.confidence * 100).toFixed(1);
                
                item.innerHTML = `
                    <div>
                        <i class="fas fa-${vehicle.class}"></i>
                        <span>${vehicle.class}</span>
                    </div>
                    <span>${plateText}</span>
                    <span class="confidence-badge">${confidence}%</span>
                `;
                vehicleList.appendChild(item);
            });
        } else {
            vehicleList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-car"></i>
                    <p>No vehicles detected</p>
                </div>
            `;
        }
    }
    
    const fraudList = document.getElementById('fraudList');
    if (fraudList) {
        fraudList.innerHTML = '';
        
        const frauds = data.fraud_results ? data.fraud_results.filter(f => f.is_fraud) : [];
        
        if (frauds.length > 0) {
            frauds.forEach(fraud => {
                const item = document.createElement('div');
                item.className = 'list-item fraud-item';
                
                const riskLevel = fraud.confidence > 0.8 ? 'High' : fraud.confidence > 0.5 ? 'Medium' : 'Low';
                
                item.innerHTML = `
                    <div>
                        <i class="fas fa-exclamation-triangle"></i>
                        <span>${fraud.fraud_type}</span>
                    </div>
                    <span>${fraud.vehicle_class}</span>
                    <span class="status-badge status-fraud">${riskLevel}</span>
                `;
                fraudList.appendChild(item);
                
                addToHistory(fraud);
            });
        } else {
            fraudList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-check-circle"></i>
                    <p>No fraud detected</p>
                </div>
            `;
        }
    }
}

function addToHistory(item) {
    detectionHistory.unshift({
        ...item,
        timestamp: new Date().toLocaleTimeString()
    });
    
    if (detectionHistory.length > 10) {
        detectionHistory.pop();
    }
    
    updateTimeline();
}

function updateTimeline() {
    const timeline = document.getElementById('timeline');
    if (!timeline) return;
    
    timeline.innerHTML = '';
    
    detectionHistory.forEach(item => {
        const timelineItem = document.createElement('div');
        timelineItem.className = 'timeline-item';
        
        timelineItem.innerHTML = `
            <span class="timeline-time">${item.timestamp}</span>
            <div class="timeline-content">
                <strong>${item.fraud_type || 'Vehicle Detected'}</strong>
                <small>${item.vehicle_class}</small>
            </div>
            <div class="timeline-badge ${item.is_fraud ? 'fraud' : 'success'}"></div>
        `;
        
        timeline.appendChild(timelineItem);
    });
}

function captureSnapshot() {
    const videoFeed = document.getElementById('videoFeed');
    if (!videoFeed || !videoFeed.src) {
        showNotification('No video feed available', 'warning');
        return;
    }
    
    const canvas = document.createElement('canvas');
    canvas.width = videoFeed.naturalWidth || 640;
    canvas.height = videoFeed.naturalHeight || 360;
    
    const context = canvas.getContext('2d');
    context.drawImage(videoFeed, 0, 0, canvas.width, canvas.height);
    
    const link = document.createElement('a');
    link.download = `smarttag-snapshot-${Date.now()}.png`;
    link.href = canvas.toDataURL();
    link.click();
    
    showNotification('Snapshot saved', 'success');
}

function shareResults() {
    if (navigator.share) {
        navigator.share({
            title: 'SmartTag Detection Results',
            text: `Vehicles: ${document.getElementById('vehicleCount')?.textContent || '0'}, Frauds: ${document.getElementById('fraudCount')?.textContent || '0'}`,
            url: window.location.href
        }).catch(console.error);
    } else {
        showNotification('Sharing not supported', 'warning');
    }
}

function printReport() {
    const vehicleCount = document.getElementById('vehicleCount')?.textContent || '0';
    const plateCount = document.getElementById('plateCount')?.textContent || '0';
    const fraudCount = document.getElementById('fraudCount')?.textContent || '0';
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
            <head>
                <title>SmartTag Report</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    h1 { color: #4361ee; }
                    .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
                    .stat { background: #f8f9fa; padding: 20px; border-radius: 10px; }
                    .stat h3 { margin: 0 0 10px; }
                    .fraud { color: #f94144; }
                </style>
            </head>
            <body>
                <h1>SmartTag Detection Report</h1>
                <p>Generated: ${new Date().toLocaleString()}</p>
                
                <div class="stats">
                    <div class="stat">
                        <h3>Vehicles</h3>
                        <p>${vehicleCount}</p>
                    </div>
                    <div class="stat">
                        <h3>Plates</h3>
                        <p>${plateCount}</p>
                    </div>
                    <div class="stat">
                        <h3>Frauds</h3>
                        <p>${fraudCount}</p>
                    </div>
                </div>
                
                <h2>Detection History</h2>
                <ul>
                    ${detectionHistory.map(item => `<li>${item.timestamp}: ${item.fraud_type || 'Vehicle Detected'}</li>`).join('')}
                </ul>
            </body>
        </html>
    `);
    printWindow.print();
}

function handleContactSubmit(event) {
    event.preventDefault();
    
    const name = document.getElementById('name');
    const email = document.getElementById('email');
    const subject = document.getElementById('subject');
    const message = document.getElementById('message');
    
    const formData = {
        name: name ? name.value : '',
        email: email ? email.value : '',
        subject: subject ? subject.value : '',
        message: message ? message.value : ''
    };
    
    console.log('Contact form submitted:', formData);
    showNotification('Thank you for your message! We will contact you soon.', 'success');
    event.target.reset();
}

function initializeDashboard() {
    loadDashboardData();
    initializeDashboardCharts();
    loadSampleTransactions();
}

async function loadDashboardData() {
    try {
        const response = await fetch('http://localhost:5000/api/get_statistics');
        const data = await response.json();
        
        if (data.success) {
            updateDashboardStats(data.statistics);
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        // Load sample data as fallback
        loadSampleDashboardData();
    }
}

function loadSampleDashboardData() {
    const totalVehicles = document.getElementById('totalVehicles');
    const totalFraud = document.getElementById('totalFraud');
    const fraudRate = document.getElementById('fraudRate');
    
    if (totalVehicles) totalVehicles.textContent = '830';
    if (totalFraud) totalFraud.textContent = '87';
    if (fraudRate) fraudRate.textContent = '10.5%';
    
    const lastUpdated = document.getElementById('lastUpdated');
    if (lastUpdated) lastUpdated.textContent = new Date().toLocaleString();
}

function initializeDashboardCharts() {
    const fraudCtx = document.getElementById('fraudChart')?.getContext('2d');
    if (fraudCtx) {
        charts.fraud = new Chart(fraudCtx, {
            type: 'doughnut',
            data: {
                labels: ['Class Mismatch', 'Unregistered', 'Invalid Plate', 'Other'],
                datasets: [{
                    data: [45, 30, 15, 10],
                    backgroundColor: ['#f94144', '#f8961e', '#f9c74f', '#90be6d'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
    
    const vehicleCtx = document.getElementById('vehicleChart')?.getContext('2d');
    if (vehicleCtx) {
        charts.vehicle = new Chart(vehicleCtx, {
            type: 'bar',
            data: {
                labels: ['Car', 'Motorcycle', 'Bus', 'Truck'],
                datasets: [{
                    label: 'Vehicles',
                    data: [120, 45, 30, 25],
                    backgroundColor: '#4361ee',
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { display: false } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
    
    const hourlyCtx = document.getElementById('hourlyChart')?.getContext('2d');
    if (hourlyCtx) {
        charts.hourly = new Chart(hourlyCtx, {
            type: 'line',
            data: {
                labels: ['00', '04', '08', '12', '16', '20'],
                datasets: [{
                    label: 'Transactions',
                    data: [15, 8, 45, 78, 92, 55],
                    borderColor: '#4cc9f0',
                    backgroundColor: 'rgba(76,201,240,0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true },
                    x: { grid: { display: false } }
                }
            }
        });
    }
    
    const perfCtx = document.getElementById('performanceChart')?.getContext('2d');
    if (perfCtx) {
        charts.performance = new Chart(perfCtx, {
            type: 'radar',
            data: {
                labels: ['Detection', 'OCR', 'Fraud Detection', 'Speed', 'Accuracy'],
                datasets: [{
                    label: 'Performance',
                    data: [98, 95, 92, 96, 99],
                    backgroundColor: 'rgba(67,97,238,0.2)',
                    borderColor: '#4361ee',
                    pointBackgroundColor: '#4361ee'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { r: { beginAtZero: true, max: 100 } }
            }
        });
    }
    
    // Add legends
    const fraudLegend = document.getElementById('fraudLegend');
    if (fraudLegend) {
        fraudLegend.innerHTML = `
            <div class="legend-item"><span class="legend-color" style="background:#f94144;"></span>Class Mismatch (45%)</div>
            <div class="legend-item"><span class="legend-color" style="background:#f8961e;"></span>Unregistered (30%)</div>
            <div class="legend-item"><span class="legend-color" style="background:#f9c74f;"></span>Invalid Plate (15%)</div>
            <div class="legend-item"><span class="legend-color" style="background:#90be6d;"></span>Other (10%)</div>
        `;
    }
    
    const vehicleProgress = document.getElementById('vehicleProgress');
    if (vehicleProgress) {
        vehicleProgress.innerHTML = `
            <div class="progress-item">
                <div class="progress-header"><span>Cars</span><span>450</span></div>
                <div class="progress-bar"><div class="progress-fill" style="width:90%"></div></div>
            </div>
            <div class="progress-item">
                <div class="progress-header"><span>Motorcycles</span><span>180</span></div>
                <div class="progress-bar"><div class="progress-fill" style="width:36%"></div></div>
            </div>
            <div class="progress-item">
                <div class="progress-header"><span>Buses</span><span>95</span></div>
                <div class="progress-bar"><div class="progress-fill" style="width:19%"></div></div>
            </div>
        `;
    }
    
    const hourlyStats = document.getElementById('hourlyStats');
    if (hourlyStats) {
        hourlyStats.innerHTML = `
            <div class="quick-stat"><span class="label">Peak Hour</span><span class="value">16:00</span></div>
            <div class="quick-stat"><span class="label">Peak Volume</span><span class="value">92</span></div>
            <div class="quick-stat"><span class="label">Off-Peak</span><span class="value">04:00</span></div>
            <div class="quick-stat"><span class="label">Average</span><span class="value">49/hr</span></div>
        `;
    }
}

function updateDashboardStats(stats) {
    const totalVehicles = document.getElementById('totalVehicles');
    const totalFraud = document.getElementById('totalFraud');
    const fraudRate = document.getElementById('fraudRate');
    
    if (totalVehicles) totalVehicles.textContent = stats.total_transactions || 0;
    if (totalFraud) totalFraud.textContent = stats.fraud_transactions || 0;
    if (fraudRate) fraudRate.textContent = `${(stats.fraud_rate || 0).toFixed(1)}%`;
    
    if (charts.fraud && stats.fraud_by_type) {
        charts.fraud.data.labels = stats.fraud_by_type.map(f => f.fraud_type);
        charts.fraud.data.datasets[0].data = stats.fraud_by_type.map(f => f.count);
        charts.fraud.update();
    }
}

function loadSampleTransactions() {
    const tbody = document.getElementById('transactionsBody');
    if (!tbody) return;
    
    const sampleData = [
        { time: '2024-01-15 14:23:45', plate: 'DL5CAB1234', vehicle: 'Car', fraud: 'Class Mismatch', confidence: 98, status: 'fraud' },
        { time: '2024-01-15 14:22:30', plate: 'MH12AB5678', vehicle: 'Truck', fraud: 'None', confidence: 99, status: 'verified' },
        { time: '2024-01-15 14:21:15', plate: 'KA01CD9012', vehicle: 'Motorcycle', fraud: 'Unregistered', confidence: 95, status: 'fraud' },
        { time: '2024-01-15 14:20:00', plate: 'TN07EF3456', vehicle: 'Bus', fraud: 'None', confidence: 100, status: 'verified' },
        { time: '2024-01-15 14:18:45', plate: 'GJ06GH7890', vehicle: 'Car', fraud: 'Invalid Plate', confidence: 92, status: 'fraud' }
    ];
    
    tbody.innerHTML = '';
    
    sampleData.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${item.time}</td>
            <td><span style="font-weight:600">${item.plate}</span></td>
            <td><i class="fas fa-${item.vehicle === 'Car' ? 'car' : item.vehicle === 'Motorcycle' ? 'motorcycle' : 'truck'}" style="margin-right:5px;color:var(--primary-color)"></i>${item.vehicle}</td>
            <td>${item.fraud}</td>
            <td><span class="confidence-badge">${item.confidence}%</span></td>
            <td><span class="status-badge status-${item.status}"><i class="fas ${item.status === 'verified' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${item.status}</span></td>
            <td><button class="icon-btn" onclick="viewDetails('${item.plate}')"><i class="fas fa-eye"></i></button></td>
        `;
        tbody.appendChild(row);
    });
}

function exportDashboardData() {
    const data = {
        timestamp: new Date().toISOString(),
        stats: {
            totalVehicles: document.getElementById('totalVehicles')?.textContent || '0',
            totalFraud: document.getElementById('totalFraud')?.textContent || '0',
            fraudRate: document.getElementById('fraudRate')?.textContent || '0%'
        }
    };
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `smarttag-dashboard-${Date.now()}.json`;
    a.click();
    
    showNotification('Dashboard data exported successfully', 'success');
}

function viewDetails(plate) {
    showNotification(`Viewing details for ${plate}`, 'info');
}

function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.style.display = show ? 'block' : 'none';
    }
}

function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    const titles = {
        success: 'Success',
        error: 'Error',
        warning: 'Warning',
        info: 'Information'
    };
    
    notification.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <div class="notification-content">
            <div class="notification-title">${titles[type]}</div>
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close"><i class="fas fa-times"></i></button>
    `;
    
    container.appendChild(notification);
    
    const timeout = setTimeout(() => {
        notification.remove();
    }, 5000);
    
    notification.querySelector('.notification-close').addEventListener('click', () => {
        clearTimeout(timeout);
        notification.remove();
    });
    
    notification.addEventListener('mouseenter', () => clearTimeout(timeout));
}

// Export functions
window.startCamera = startCamera;
window.stopCamera = stopCamera;
window.captureSnapshot = captureSnapshot;
window.shareResults = shareResults;
window.printReport = printReport;
window.viewDetails = viewDetails;