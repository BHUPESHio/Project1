document.addEventListener('DOMContentLoaded', () => {
  // -------------------- Shared Elements --------------------
  const authModal = document.getElementById('auth-modal');
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');
  const authButton = document.querySelector('.auth-button');
  const profileMenu = document.querySelector('.profile-menu');
  const profileIcon = document.querySelector('.profile-icon');
  const profileDropdown = document.querySelector('.profile-dropdown');
  const logoutLink = document.getElementById('logout-link');
  const closeModalBtn = document.querySelector('.close-modal');
  const goSignup = document.getElementById('go-signup');
  const goLogin = document.getElementById('go-login');
  const modalTitle = document.getElementById('modal-title');

  // -------------------- Auth Modal Logic --------------------
  if (authButton && authModal) {
    authButton.addEventListener('click', () => {
      authModal.classList.remove('hidden');
      switchAuthTab('login');
    });
  }

  if (closeModalBtn) {
    closeModalBtn.addEventListener('click', () => authModal.classList.add('hidden'));
  }

  if (goSignup) goSignup.addEventListener('click', () => switchAuthTab('signup'));
  if (goLogin) goLogin.addEventListener('click', () => switchAuthTab('login'));

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

  loginForm?.addEventListener('submit', async (e) => {
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
      authButton?.classList.add('hidden');
      profileMenu?.classList.remove('hidden');
    } else {
      alert(result.message || "Login failed");
    }
  });

  signupForm?.addEventListener('submit', async (e) => {
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
      alert("Signup successful!");
      authModal.classList.add('hidden');
      authButton?.classList.add('hidden');
      profileMenu?.classList.remove('hidden');
    } else {
      alert(result.message || "Signup failed");
    }
  });

  profileIcon?.addEventListener('click', () => {
    profileDropdown?.classList.toggle('hidden');
  });

  logoutLink?.addEventListener('click', async () => {
    const res = await fetch('/logout');
    const result = await res.json();
    if (result.success) {
      alert("Logged out!");
      window.location.href = '/';
    }
  });

  // -------------------- BMI Logic --------------------
  const bmiForm = document.getElementById('bmi-form');
  if (bmiForm) {
    const ageInput = document.getElementById('age');
    const genderGroup = document.querySelector('.child-only');
    const resultDiv = document.getElementById('bmi-result');
    const unitRadios = document.getElementsByName('units');
    const weightInput = document.getElementById('weight');
    const heightInput = document.getElementById('height');
    const bmiChartCanvas = document.getElementById('bmiChart');
    let bmiChart;

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
      weightInput.placeholder = units === 'metric' ? 'Weight in kg' : 'Weight in lbs';
      heightInput.placeholder = units === 'metric' ? 'Height in cm' : 'Height in inches';
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
      }
    });

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
                label: (context) => `${context.label} → Up to ${context.raw}`
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

    // BMI chart data
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
  }

  // -------------------- Body Fat Logic --------------------
  const bodyFatForm = document.getElementById("bodyfat-form");
  if (bodyFatForm) {
    const genderInput = document.getElementById("gender");
    const hipContainer = document.getElementById("hipContainer");
    const resultDiv = document.getElementById("result");
    const chartCanvas = document.getElementById("bodyFatChart");
    let bodyFatChart;

    genderInput.addEventListener("change", function () {
      if (this.value === "female") {
        hipContainer.style.display = "block";
        document.getElementById("hip").required = true;
      } else {
        hipContainer.style.display = "none";
        document.getElementById("hip").required = false;
      }
      resetChart();
    });

    bodyFatForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const gender = genderInput.value;
      const height = parseFloat(document.getElementById("height").value);
      const neck = parseFloat(document.getElementById("neck").value);
      const waist = parseFloat(document.getElementById("waist").value);
      const hip = gender === "female" ? parseFloat(document.getElementById("hip").value) : 0;

      const response = await fetch("/api/calculate_bodyfat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ gender, height, neck, waist, hip })
      });

      const data = await response.json();

      if (data.success) {
        const percentage = data.body_fat;
        resultDiv.innerHTML = `Your Body Fat Percentage is <strong>${percentage}%</strong>`;
        drawBodyFatChart(gender, percentage);
      } else {
        resultDiv.innerHTML = `<span style="color:red;">${data.error || "Calculation failed"}</span>`;
        resetChart();
      }
    });

    function drawBodyFatChart(gender, userValue) {
      function drawBodyFatChart(gender, userValue) {
  const zones = {
    male: {
      labels: ["Essential", "Athletes", "Fitness", "Average", "Obese"],
      values: [5, 13, 17, 24, 40],
      colors: ["#2a9d8f", "#38b000", "#f4a261", "#f77f00", "#d62828"]
    },
    female: {
      labels: ["Essential", "Athletes", "Fitness", "Average", "Obese"],
      values: [13, 20, 24, 31, 45],
      colors: ["#2a9d8f", "#38b000", "#f4a261", "#f77f00", "#d62828"]
    }
  };

  const config = zones[gender];
  const index = config.values.findIndex(v => userValue <= v);
  const highlightIndex = index >= 0 ? index : config.values.length - 1;

  // ✅ Destroy chart safely if already created
  if (Chart.getChart(chartCanvas)) {
    Chart.getChart(chartCanvas).destroy();
  }

  bodyFatChart = new Chart(chartCanvas, {
    type: "bar",
    data: {
      labels: config.labels,
      datasets: [{
        label: "Body Fat % Zones",
        data: config.values,
        backgroundColor: config.colors.map((c, i) => i === highlightIndex ? "#1d3557" : c)
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              const start = ctx.dataIndex === 0 ? 0 : config.values[ctx.dataIndex - 1];
              const end = config.values[ctx.dataIndex];
              return `${start}% - ${end}%`;
            }
          }
        }
      },
      scales: {
        x: { beginAtZero: true },
        y: { ticks: { autoSkip: false } }
      }
    }
  });
}
//-----------------Ideal Weight --------------------------


  const form = document.getElementById("idealweight-form");
  if (!form) return;

  const resultDiv = document.getElementById("idealweight-result");
  const genderSelect = document.getElementById("gender");
  const unitRadios = document.getElementsByName("units");
  const chartCanvas = document.getElementById("idealWeightChart");
  let idealChart;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const gender = genderSelect.value;
    const height = parseFloat(document.getElementById("height").value);
    const age = parseInt(document.getElementById("age").value);
    const units = [...unitRadios].find(r => r.checked).value;

    const res = await fetch("/api/calculate_idealweight", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gender, height, age, units })
    });

    const data = await res.json();

    if (data.success) {
      const label = units === "metric" ? `${data.ideal_weight_kg} kg` : `${data.ideal_weight_lb} lbs`;
      resultDiv.innerHTML = `Your ideal weight is <strong>${label}</strong>`;
      resultDiv.classList.remove("hidden");

      drawChart(gender, data.ideal_weight_kg);
    } else {
      resultDiv.innerHTML = `<span style="color:red;">${data.error}</span>`;
    }
  });

  function drawChart(gender, value) {
    if (idealChart) idealChart.destroy();

    const ranges = {
      male: [50, 65, 75, 85, 95],
      female: [45, 55, 65, 75, 85]
    };

    const labels = ["Very Low", "Low", "Ideal", "High", "Very High"];
    const colors = ["#90caf9", "#a5d6a7", "#66bb6a", "#ffa726", "#ef5350"];

    const index = ranges[gender].findIndex(v => value <= v);
    const highlight = index === -1 ? ranges[gender].length - 1 : index;

    idealChart = new Chart(chartCanvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: "Ideal Weight Zones (kg)",
          data: ranges[gender],
          backgroundColor: colors.map((c, i) => i === highlight ? "#1d3557" : c)
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true }
        },
        plugins: {
          legend: { display: false }
        }
      }
    });
  }





    function resetChart() {
      if (bodyFatChart) {
        bodyFatChart.destroy();
        bodyFatChart = null;
      }
    }
  }
}

const calorieForm = document.getElementById('calorie-form');
if (calorieForm) {
    calorieForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const age = document.getElementById('cal-age').value;
        const gender = document.getElementById('cal-gender').value;
        const weight = document.getElementById('cal-weight').value;
        const height = document.getElementById('cal-height').value;
        const activity = document.getElementById('cal-activity').value;
        const units = document.querySelector('input[name="cal-units"]:checked').value;

        const res = await fetch('/api/calculate_calories', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ age, gender, weight, height, activity_level: activity, units })
        });

        const data = await res.json();
        const resultDiv = document.getElementById('calorie-result');
        resultDiv.classList.remove('hidden');
        resultDiv.textContent = data.success
            ? `Recommended Daily Calories: ${data.daily_calories} kcal`
            : `Error: ${data.error}`;
    });
}
});

// -------------------- BMI Prediction Chart Logic --------------------
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('predict-form');
  const resultBox = document.getElementById('predict-result');
  const chartCanvas = document.getElementById('predictionChart');
  let chart;

  if (!form || !chartCanvas || !resultBox) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const age = parseInt(document.getElementById('age').value);
    const bmi = parseFloat(document.getElementById('bmi').value);

    const res = await fetch('/api/predict_bmi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ age, bmi })
    });

    const data = await res.json();

    if (data.success) {
      const { predicted_bmi, suggestions, prediction_timeline } = data;

      resultBox.innerHTML = `
        <p><strong>Predicted BMI (6 months later):</strong> ${predicted_bmi}</p>
        <p><strong>Suggestion:</strong> ${suggestions}</p>
      `;
      resultBox.classList.remove("hidden");

      if (chart) chart.destroy();

      chart = new Chart(chartCanvas, {
        type: 'Bar',
        data: {
          labels: prediction_timeline.map(p => p.date),
          datasets: [{
            label: 'BMI Prediction',
            data: prediction_timeline.map(p => p.bmi),
            borderColor: '#9c27b0',
            fill: false,
            tension: 0.3
          }]
        },
        options: {
          responsive: true,
          scales: {
            y: {
              beginAtZero: true,
              title: { display: true, text: 'BMI' }
            },
            x: {
              title: { display: true, text: 'Month' }
            }
          }
        }
      });
    } else {
      resultBox.innerHTML = `<p style="color:red;">${data.error || 'Prediction failed'}</p>`;
      resultBox.classList.remove("hidden");
    }
  });
});
