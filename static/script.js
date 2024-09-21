document.addEventListener('DOMContentLoaded', function() {
    // Sélection des éléments DOM
    const searchForm = document.getElementById('search-form');
    const loadingIndicator = document.getElementById('loading');
    const bookCarousel = document.querySelector('.book-carousel');
    const prevButton = document.getElementById('prev-book');
    const nextButton = document.getElementById('next-book');
    const chatbotForm = document.getElementById('chatbot-form');
    const chatbotMessages = document.getElementById('chatbot-messages');
    const darkModeToggle = document.getElementById('dark-mode-toggle');

    let currentBookIndex = 0;
    let books = [];

    // Initialisation du son de page
    const pageFlipSound = new Howl({
        src: ['/static/page-flip.mp3']
    });

    // Gestion du mode sombre
    function toggleDarkMode() {
        document.body.classList.toggle('dark-mode');
        const isDarkMode = document.body.classList.contains('dark-mode');
        localStorage.setItem('darkMode', isDarkMode);
        darkModeToggle.innerHTML = isDarkMode ? '<i class="fas fa-sun"></i>' : '<i class="fas fa-moon"></i>';
        updateChartsTheme(isDarkMode);
    }

    darkModeToggle.addEventListener('click', toggleDarkMode);

    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
        darkModeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    }

    // Navigation
    document.querySelectorAll('nav a').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            smoothScroll(targetId, 1000);
            updateActiveNavLink(this);
        });
    });

    function updateActiveNavLink(clickedLink) {
        document.querySelector('nav a.active').classList.remove('active');
        clickedLink.classList.add('active');
    }

    // Recherche de livres
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const searchQuery = document.getElementById('search-input').value.trim();
        if (searchQuery) {
            loadingIndicator.style.display = 'block';
            searchBooks(searchQuery);
        }
    });

    function searchBooks(query) {
        createNotification('Recherche en cours...', 'info');
        fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            loadingIndicator.style.display = 'none';
            if (data.length > 0) {
                books = data;
                currentBookIndex = 0;
                displayBooks();
                createNotification('Recherche terminée !', 'success');
            } else {
                bookCarousel.innerHTML = '<p>Aucun livre trouvé pour cette recherche.</p>';
                createNotification('Aucun résultat trouvé', 'warning');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            loadingIndicator.style.display = 'none';
            bookCarousel.innerHTML = '<p>Une erreur s\'est produite lors de la recherche.</p>';
            createNotification('Erreur lors de la recherche', 'error');
        });
    }

    // Affichage des livres dans le carrousel
    function displayBooks() {
        bookCarousel.innerHTML = '';
        for (let i = -1; i <= 1; i++) {
            if (books.length > 0) {
                const index = (currentBookIndex + i + books.length) % books.length;
                const book = books[index];
                const bookElement = createBookElement(book, i);
                bookCarousel.appendChild(bookElement);

                // Animation d'apparition
                setTimeout(() => {
                    bookElement.style.opacity = '1';
                    bookElement.style.transform = 'translateX(0) rotateY(0) scale(1)';
                }, 50 * (i + 2));
            }
        }
    }

    function createBookElement(book, position) {
        const bookElement = document.createElement('div');
        bookElement.className = `book ${position === -1 ? 'prev' : position === 0 ? 'active' : 'next'}`;
        
        const imageUrl = book['Image-URL-L'] && book['Image-URL-L'].startsWith('http') 
            ? book['Image-URL-L'] 
            : '/static/default-book-cover.jpg';

        const yearOfPublication = book['Year-Of-Publication'] === '0' || book['Year-Of-Publication'] === '2037' 
            ? '2022' 
            : book['Year-Of-Publication'];

        bookElement.innerHTML = `
            <img src="${imageUrl}" alt="${book['Book-Title']}" loading="lazy">
            <h3>${book['Book-Title']}</h3>
            <p>${book['Book-Author']}</p>
            <p>${yearOfPublication}</p>
            <div class="book-comment">${book['comment'] || 'Pas de commentaire disponible.'}</div>
        `;

        return bookElement;
    }

    // Navigation dans le carrousel
    prevButton.addEventListener('click', () => navigateCarousel('prev'));
    nextButton.addEventListener('click', () => navigateCarousel('next'));

    function navigateCarousel(direction) {
        if (books.length > 0) {
            currentBookIndex = direction === 'next' 
                ? (currentBookIndex + 1) % books.length
                : (currentBookIndex - 1 + books.length) % books.length;
            transitionBooks(direction);
            pageFlipSound.play();
        }
    }

    function transitionBooks(direction) {
        const books = bookCarousel.querySelectorAll('.book');
        books.forEach(book => {
            book.style.transition = 'all 0.5s ease';
        });

        if (direction === 'next') {
            books[0].classList.remove('prev');
            books[0].classList.add('next');
            books[1].classList.remove('active');
            books[1].classList.add('prev');
            books[2].classList.remove('next');
            books[2].classList.add('active');
        } else {
            books[0].classList.remove('prev');
            books[0].classList.add('active');
            books[1].classList.remove('active');
            books[1].classList.add('next');
            books[2].classList.remove('next');
            books[2].classList.add('prev');
        }

        // Animer le livre actif
        setTimeout(() => {
            const activeBook = bookCarousel.querySelector('.book.active');
            activeBook.style.transform = 'scale(1.05)';
            setTimeout(() => {
                activeBook.style.transform = 'scale(1)';
            }, 300);
        }, 500);

        // Mettre à jour l'affichage après la transition
        setTimeout(displayBooks, 500);
    }

    // Fonctionnalité de l'assistant IA
    chatbotForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = document.getElementById('chatbot-input').value.trim();
        if (message) {
            appendMessage('Vous', message);
            document.getElementById('chatbot-input').value = '';
            getChatbotResponse(message);
        }
    });

    function getChatbotResponse(message) {
        appendTypingAnimation();
        fetch('/chatbot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            removeTypingAnimation();
            appendMessage('Assistant', data.response);
            if (data.books && data.books.length > 0) {
                appendRecommendedBooks(data.books);
            }
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
            removeTypingAnimation();
            appendMessage('Assistant', 'Désolé, une erreur s\'est produite.');
        });
    }

    function appendMessage(sender, message) {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${sender.toLowerCase()}`;
        messageElement.innerHTML = `<strong>${sender}:</strong> ${message}`;
        messageElement.style.opacity = '0';
        chatbotMessages.appendChild(messageElement);

        setTimeout(() => {
            messageElement.style.opacity = '1';
            messageElement.style.transform = 'translateY(0)';
        }, 50);
    }

    function appendTypingAnimation() {
        const typingElement = document.createElement('div');
        typingElement.className = 'typing-animation';
        typingElement.innerHTML = '<span></span><span></span><span></span>';
        chatbotMessages.appendChild(typingElement);
    }

    function removeTypingAnimation() {
        const typingElement = chatbotMessages.querySelector('.typing-animation');
        if (typingElement) {
            typingElement.remove();
        }
    }


function appendRecommendedBooks(books) {
    const booksContainerWrapper = document.createElement('div');
    booksContainerWrapper.className = 'chatbot-books-container';
    
    const booksContainer = document.createElement('div');
    booksContainer.className = 'chatbot-books';
    
    books.forEach((book, index) => {
        const bookElement = createChatbotBookElement(book, index);
        booksContainer.appendChild(bookElement);
    });
    
    booksContainerWrapper.appendChild(booksContainer);

    const controlsElement = document.createElement('div');
    controlsElement.className = 'chatbot-books-controls';
    controlsElement.innerHTML = `
        <button id="prev-chatbot-book"><i class="fas fa-chevron-left"></i></button>
        <button id="next-chatbot-book"><i class="fas fa-chevron-right"></i></button>
    `;
    booksContainerWrapper.appendChild(controlsElement);

    chatbotMessages.appendChild(booksContainerWrapper);

    initializeChatbotBooksNavigation(booksContainer);
}

    function createChatbotBookElement(book, index) {
        const bookElement = document.createElement('div');
        bookElement.className = `chatbot-book ${index === 0 ? 'active' : index === 1 ? 'next' : 'prev'}`;
        
        const imageUrl = book['Image-URL-L'] && book['Image-URL-L'].startsWith('http') 
            ? book['Image-URL-L'] 
            : '/static/default-book-cover.jpg';

        const yearOfPublication = book['Year-Of-Publication'] === '0' || book['Year-Of-Publication'] === '2037' 
            ? '2022' 
            : book['Year-Of-Publication'];

        bookElement.innerHTML = `
            <img src="${imageUrl}" alt="${book['Book-Title']}" loading="lazy">
            <div class="chatbot-book-info">
                <p class="chatbot-book-title">${book['Book-Title']}</p>
                <p class="chatbot-book-author">par ${book['Book-Author']}</p>
                <p class="chatbot-book-year">${yearOfPublication}</p>
            </div>
        `;

        return bookElement;
    }

    function initializeChatbotBooksNavigation(booksContainer) {
        const prevButton = document.getElementById('prev-chatbot-book');
        const nextButton = document.getElementById('next-chatbot-book');
        const books = booksContainer.querySelectorAll('.chatbot-book');
        let currentIndex = 0;

        function updateBookClasses() {
            books.forEach((book, index) => {
                book.className = 'chatbot-book';
                if (index === currentIndex) {
                    book.classList.add('active');
                } else if (index === (currentIndex + 1) % books.length) {
                    book.classList.add('next');
                } else if (index === (currentIndex - 1 + books.length) % books.length) {
                    book.classList.add('prev');
                }
            });
        }

        prevButton.addEventListener('click', () => {
            currentIndex = (currentIndex - 1 + books.length) % books.length;
            updateBookClasses();
        });

        nextButton.addEventListener('click', () => {
            currentIndex = (currentIndex + 1) % books.length;
            updateBookClasses();
        });
    }

    // Initialisation des graphiques du dashboard
    let charts = {};

    function createDashboardCharts() {
        createTopRatedBooksChart();
        createTopReadByCountryChart();
        createPopularGenresChart();
        createReadingTrendsChart();
    }

    function createTopRatedBooksChart() {
        fetch('/top_rated_books')
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('topRatedChart').getContext('2d');
                charts.topRated = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: 'Note moyenne',
                            data: data.values,
                            backgroundColor: 'rgba(75, 192, 192, 0.6)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                max: 10
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            },
                            title: {
                                display: true,
                                text: 'Top 5 des livres les mieux notés'
                            }
                        }
                    }
                });
            });
    }

    function createTopReadByCountryChart() {
        fetch('/top_read_by_country')
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('topReadByCountryChart').getContext('2d');
                charts.topReadByCountry = new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.values,
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.8)',
                                'rgba(54, 162, 235, 0.8)',
                                'rgba(255, 206, 86, 0.8)',
                                'rgba(75, 192, 192, 0.8)',
                                'rgba(153, 102, 255, 0.8)'
                            ],
                            borderColor: 'rgba(255, 255, 255, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'right'
                            },
                            title: {
                                display: true,
                                text: 'Top 5 des pays les plus lecteurs'
                            }
                        }
                    }
                });
            });
    }

    function createPopularGenresChart() {
        fetch('/popular_genres')
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('popularGenresChart').getContext('2d');
                charts.popularGenres = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.values,
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.8)',
                                'rgba(54, 162, 235, 0.8)',
                                'rgba(255, 206, 86, 0.8)',
                                'rgba(75, 192, 192, 0.8)',
                                'rgba(153, 102, 255, 0.8)'
                            ],
                            borderColor: 'rgba(255, 255, 255, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'right'
                            },
                            title: {
                                display: true,
                                text: 'Genres les plus populaires'
                            }
                        }
                    }
                });
            });
    }

    function createReadingTrendsChart() {
        fetch('/reading_trends')
            .then(response => response.json())
            .then(data => {
                const ctx = document.getElementById('readingTrendsChart').getContext('2d');
                charts.readingTrends = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: 'Livres lus',
                            data: data.values,
                            borderColor: 'rgba(75, 192, 192, 1)',
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            tension: 0.1,
                            fill: true
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        },
                        plugins: {
                            legend: {
                                display: false
                            },
                            title: {
                                display: true,
                                text: 'Tendances de lecture par mois'
                            }
                        }
                    }
                });
            });
    }

    // Mise à jour des thèmes des graphiques
    function updateChartsTheme(isDarkMode) {
        const textColor = isDarkMode ? '#f2e9e4' : '#22223b';
        const gridColor = isDarkMode ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

        Object.values(charts).forEach(chart => {
            chart.options.plugins.title.color = textColor;
            chart.options.plugins.legend.labels.color = textColor;
            chart.options.scales.x.ticks.color = textColor;
            chart.options.scales.y.ticks.color = textColor;
            chart.options.scales.x.grid.color = gridColor;
            chart.options.scales.y.grid.color = gridColor;
            chart.update();
        });
    }

    // Fonction pour le défilement fluide
    function smoothScroll(targetId, duration) {
        const target = document.getElementById(targetId);
        const targetPosition = target.getBoundingClientRect().top + window.pageYOffset;
        const startPosition = window.pageYOffset;
        const distance = targetPosition - startPosition;
        let startTime = null;

        function animation(currentTime) {
            if (startTime === null) startTime = currentTime;
            const timeElapsed = currentTime - startTime;
            const run = ease(timeElapsed, startPosition, distance, duration);
            window.scrollTo(0, run);
            if (timeElapsed < duration) requestAnimationFrame(animation);
        }

        function ease(t, b, c, d) {
            t /= d / 2;
            if (t < 1) return c / 2 * t * t + b;
            t--;
            return -c / 2 * (t * (t - 2) - 1) + b;
        }

        requestAnimationFrame(animation);
    }

    // Effet parallaxe
    function parallax() {
        const elements = document.querySelectorAll('.parallax');
        elements.forEach(element => {
            const speed = element.dataset.speed;
            element.style.transform = `translateY(${window.pageYOffset * speed}px)`;
        });
    }

    window.addEventListener('scroll', parallax);

    // Animation au défilement
    function revealOnScroll() {
        const reveals = document.querySelectorAll(".reveal");
        reveals.forEach(reveal => {
            const windowHeight = window.innerHeight;
            const elementTop = reveal.getBoundingClientRect().top;
            const elementVisible = 150;
            if (elementTop < windowHeight - elementVisible) {
                reveal.classList.add("active");
            } else {
                reveal.classList.remove("active");
            }
        });
    }

    window.addEventListener("scroll", revealOnScroll);

    // Système de notification
    function createNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }

    // Autocomplétion de la recherche
    function autocomplete(inp, arr) {
        let currentFocus;
        inp.addEventListener("input", function(e) {
            let a, b, i, val = this.value;
            closeAllLists();
            if (!val) { return false; }
            currentFocus = -1;
            a = document.createElement("DIV");
            a.setAttribute("id", this.id + "autocomplete-list");
            a.setAttribute("class", "autocomplete-items");
            this.parentNode.appendChild(a);
            for (i = 0; i < arr.length; i++) {
                if (arr[i].substr(0, val.length).toUpperCase() == val.toUpperCase()) {
                    b = document.createElement("DIV");
                    b.innerHTML = "<strong>" + arr[i].substr(0, val.length) + "</strong>";
                    b.innerHTML += arr[i].substr(val.length);
                    b.innerHTML += "<input type='hidden' value='" + arr[i] + "'>";
                    b.addEventListener("click", function(e) {
                        inp.value = this.getElementsByTagName("input")[0].value;
                        closeAllLists();
                    });
                    a.appendChild(b);
                }
            }
        });

        inp.addEventListener("keydown", function(e) {
            let x = document.getElementById(this.id + "autocomplete-list");
            if (x) x = x.getElementsByTagName("div");
            if (e.keyCode == 40) {
                currentFocus++;
                addActive(x);
            } else if (e.keyCode == 38) {
                currentFocus--;
                addActive(x);
            } else if (e.keyCode == 13) {
                e.preventDefault();
                if (currentFocus > -1) {
                    if (x) x[currentFocus].click();
                }
            }
        });

        function addActive(x) {
            if (!x) return false;
            removeActive(x);
            if (currentFocus >= x.length) currentFocus = 0;
            if (currentFocus < 0) currentFocus = (x.length - 1);
            x[currentFocus].classList.add("autocomplete-active");
        }

        function removeActive(x) {
            for (let i = 0; i < x.length; i++) {
                x[i].classList.remove("autocomplete-active");
            }
        }

        function closeAllLists(elmnt) {
            const x = document.getElementsByClassName("autocomplete-items");
            for (let i = 0; i < x.length; i++) {
                if (elmnt != x[i] && elmnt != inp) {
                    x[i].parentNode.removeChild(x[i]);
                }
            }
        }

        document.addEventListener("click", function (e) {
            closeAllLists(e.target);
        });
    }

    // Initialisation de l'autocomplétion
    autocomplete(document.getElementById("search-input"), ["Harry Potter", "Le Seigneur des Anneaux", "1984", "Orgueil et Préjugés"]);

    // Initialisation des tooltips
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseenter', () => {
            const tooltipText = document.createElement('div');
            tooltipText.className = 'tooltip';
            tooltipText.textContent = tooltip.dataset.tooltip;
            document.body.appendChild(tooltipText);

            const rect = tooltip.getBoundingClientRect();
            tooltipText.style.top = `${rect.bottom + window.scrollY}px`;
            tooltipText.style.left = `${rect.left + window.scrollX}px`;

            setTimeout(() => tooltipText.classList.add('show'), 10);
        });

        tooltip.addEventListener('mouseleave', () => {
            const tooltipText = document.querySelector('.tooltip');
            if (tooltipText) {
                tooltipText.classList.remove('show');
                setTimeout(() => tooltipText.remove(), 200);
            }
        });
    });

    // Initialisation
    createDashboardCharts();
    revealOnScroll();
});