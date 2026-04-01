const form = document.getElementById('recForm');
const titleInput = document.getElementById('movieTitle');
const results = document.getElementById('results');
const recList = document.getElementById('recList');
const movieBanner = document.getElementById('movieBanner');
const bannerTitle = document.getElementById('bannerTitle');
const bannerTagline = document.getElementById('bannerTagline');
const bannerMeta = document.getElementById('bannerMeta');
const bannerOverview = document.getElementById('bannerOverview');

let bannerTimer = null;
let lastSearchBannerData = null;

form.addEventListener('submit', async function(e) {
    e.preventDefault();

    const title = titleInput.value.trim();
    if (!title) {
        alert('Please enter a movie title.');
        return;
    }

    results.style.display = 'block';
    recList.innerHTML = '<div class="text-center p-4"><div class="spinner-border text-primary" role="status"></div></div>';

    try {
        const response = await fetch('/recommend', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title})
        });

        const data = await response.json();

        if (data.recommendations && data.recommendations.length > 0) {
            recList.innerHTML = data.recommendations.map(rec => 
                `<div class="list-group-item" data-title="${rec}"><strong>${rec}</strong></div>`
            ).join('');
            attachHoverListeners();
        } else {
            recList.innerHTML = '<div class="alert alert-info">No recommendations found. Try another title!</div>';
        }
    } catch (error) {
        recList.innerHTML = '<div class="alert alert-danger">Error fetching recommendations.</div>';
        console.error(error);
    }
});

titleInput.addEventListener('input', function() {
    const title = this.value.trim();
    this.style.backgroundColor = '#f0f8ff';
    setTimeout(() => { this.style.backgroundColor = ''; }, 200);

    clearTimeout(bannerTimer);
    if (title.length < 2) {
        hideBanner();
        return;
    }

    bannerTimer = setTimeout(() => fetchMovieBanner(title, false), 300);
});

async function fetchMovieBanner(title, isHover = false) {
    try {
        const response = await fetch('/movie_info', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({title})
        });
        const data = await response.json();

        if (data.found) {
            showBanner(data, isHover);
        } else {
            if (!isHover) hideBanner();
        }
    } catch (error) {
        console.error(error);
        if (!isHover) hideBanner();
    }
}

function attachHoverListeners() {
    const items = recList.querySelectorAll('.list-group-item');
    items.forEach(item => {
        item.addEventListener('mouseenter', () => {
            const movieTitle = item.dataset.title;
            if (movieTitle) {
                fetchMovieBanner(movieTitle, true);
            }
        });
        item.addEventListener('mouseleave', () => {
            if (lastSearchBannerData) {
                showBanner(lastSearchBannerData, false);
            }
        });
    });
}

function showBanner(data, isHover = false) {
    bannerTitle.textContent = data.title;
    bannerTagline.textContent = data.tagline || '';
    bannerMeta.textContent = [data.release_date, data.vote_average ? `Rating: ${data.vote_average}` : '']
        .filter(Boolean)
        .join(' • ');
    bannerOverview.textContent = data.overview || '';
    movieBanner.style.display = 'block';

    if (!isHover) {
        lastSearchBannerData = data;
    }
}

function hideBanner() {
    movieBanner.style.display = 'none';
    bannerTitle.textContent = '';
    bannerTagline.textContent = '';
    bannerMeta.textContent = '';
    bannerOverview.textContent = '';
    lastSearchBannerData = null;
}

