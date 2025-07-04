document.addEventListener('DOMContentLoaded', () => {

    const ageInput = document.getElementById('age');
    const genderGroup = document.querySelector('.child-only');
    const bmiForm = document.getElementById('bmi-form');
    const resultDiv = document.getElementById('bmi-result');
    const unitRadios = document.getElementsByName('units');
    const weightInput = document.getElementById('weight');
    const heightInput = document.getElementById('height');
    const bmiChartCanvas = document.getElementById('bmiChart');
    let bmiChart;


    const profileMenu = document.querySelector('.profile-menu');
    const profileIcon = document.querySelector('.profile-icon');
    const profileDropdown = document.querySelector('.profile-dropdown');
    const authButton = document.querySelector('.auth-button');
    const logoutLink = document.getElementById('logout-link');

// Show dropdown on icon click
if (profileIcon) {
    profileIcon.addEventListener('click', () => {
        profileDropdown.classList.toggle('hidden');
    });
}

// Logout handler
if (logoutLink) {
    logoutLink.addEventListener('click', async () => {
        const res = await fetch('/logout');
        const result = await res.json();
        if (result.success) {
            alert("Logged out!");
            window.location.href = '/';
        }
    });
}




    

// Auth Modal Logic
const authModal = document.getElementById('auth-modal');
const loginForm = document.getElementById('login-form');
const signupForm = document.getElementById('signup-form');
const closeModalBtn = document.querySelector('.close-modal');
const goSignup = document.getElementById('go-signup');
const goLogin = document.getElementById('go-login');
const modalTitle = document.getElementById('modal-title');


loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = loginForm.querySelector('input[type="email"]').value;
    const password = loginForm.querySelector('input[type="password"]').value;

    const res = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });

    const result = await res.json();
    if (result.success) {
        alert("Logged in successfully!");
        authModal.classList.add('hidden');
        authButton.classList.add('hidden')
        profileMenu.classList.remove('hidden')
    } else {
        alert(result.message || "Login failed");
    }
});

signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const inputs = signupForm.querySelectorAll('input');
    const name = inputs[0].value;
    const email = inputs[1].value;
    const password = inputs[2].value;

    const res = await fetch('/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password })
    });

    const result = await res.json();
    if (result.success) {
        alert("Signup successful! Verify your account before log-in.");
        authButton.classList.add('hidden');
        profileMenu.classList.remove('hidden');
        authModal.classList.add('hidden');
    } else {
        alert(result.message || "Signup failed");
    }
});




if (authButton && authModal) {
    authButton.addEventListener('click', () => {
        authModal.classList.remove('hidden');
        switchAuthTab('login');
    });
}

if (closeModalBtn) {
    closeModalBtn.addEventListener('click', () => {
        authModal.classList.add('hidden');
    });
}

if (goSignup) {
    goSignup.addEventListener('click', () => switchAuthTab('signup'));
}

if (goLogin) {
    goLogin.addEventListener('click', () => switchAuthTab('login'));
}

function switchAuthTab(tab) {
    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        signupForm.classList.add('hidden');
        modalTitle.textContent = "Login";
    } else {
        loginForm.classList.add('hidden');
        signupForm.classList.remove('hidden');
        modalTitle.textContent = "Sign Up";
    }
}



        const resetForm = () => {
        resultDiv.classList.add('hidden');
        resultDiv.textContent = '';
        weightInput.value = '';
        heightInput.value = '';
        ageInput.value = '';
        genderGroup.classList.add('hidden');
        if (bmiChart) bmiChart.destroy();
    };

    const updatePlaceholders = () => {
        const units = document.querySelector('input[name="units"]:checked').value;
        if (units === 'metric') {
            weightInput.placeholder = 'Weight in kg';
            heightInput.placeholder = 'Height in cm';
        } else {
            weightInput.placeholder = 'Weight in lbs';
            heightInput.placeholder = 'Height in inches';
        }
    };

    unitRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            resetForm();
            updatePlaceholders();
        });
    });

    updatePlaceholders();

    ageInput.addEventListener('input', () => {
        const age = parseInt(ageInput.value);
        if (age < 19 && age >= 2) {
            genderGroup.classList.remove('hidden');
        } else {
            genderGroup.classList.add('hidden');
        }
    });

    bmiForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const age = parseInt(ageInput.value);
        const weight = parseFloat(weightInput.value);
        const height = parseFloat(heightInput.value);
        const units = document.querySelector('input[name="units"]:checked').value;

        if (!weight || !height || !age || age < 2) return;

        const response = await fetch('/api/calculate_bmi', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ age, weight, height, units })
        });

        const result = await response.json();
        resultDiv.classList.remove('hidden');

        if (bmiChart) bmiChart.destroy();

        if (result.type === 'child') {
            resultDiv.textContent = `Your BMI: ${result.bmi} | Percentile: ${result.percentile} | Category: ${result.category}`;
            renderChart(childBmiJson, 'Child BMI Percentiles');
        } else {
            resultDiv.textContent = `Your BMI: ${result.bmi} | Category: ${result.category}`;
            renderChart(adultBmiJson, 'Adult BMI Ranges');
        };
    })

    function renderChart(chartData, title) {
        bmiChart = new Chart(bmiChartCanvas, {
            type: 'bar',
            data: {
                labels: chartData.labels,
                datasets: [{
                    label: title,
                    data: chartData.values,
                    backgroundColor: ['#42a5f5', '#66bb6a', '#ffa726', '#ef5350']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.label} → Up to ${context.raw}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: 'BMI Value' }
                    }
                }
            }
        });
    }

    // JSON data for adult and child charts
    window.adultBmiJson = {
        labels: ["Underweight", "Normal", "Overweight", "Obese"],
        values: [18.4, 24.9, 29.9, 40],
        categories: ["Underweight", "Normal", "Overweight", "Obese"]
    };

    window.childBmiJson = {
        labels: ["< 5th", "5th–85th", "85th–95th", "> 95th"],
        values: [14, 18, 20, 23],
        categories: ["Underweight", "Healthy", "At Risk", "Overweight"]
        };
    });
    
