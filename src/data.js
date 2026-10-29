export const categories = [
  { id: 'nature', name: 'Przyroda', icon: 'trees', color: 'green', caption: 'Złap oddech' },
  { id: 'heritage', name: 'Zabytki', icon: 'castle', color: 'sand', caption: 'Dotknij historii' },
  { id: 'bike', name: 'Trasy rowerowe', icon: 'bike', color: 'blue', caption: 'Ruszaj przed siebie' },
  { id: 'walk', name: 'Trasy piesze', icon: 'footprints', color: 'pink', caption: 'Odkrywaj krok po kroku' },
  { id: 'food', name: 'Jedzenie', icon: 'utensils', color: 'peach', caption: 'Posmakuj regionu' },
  { id: 'stay', name: 'Noclegi', icon: 'bed', color: 'purple', caption: 'Zostań na dłużej' },
]
export const places = [
  { id: 1, name: 'Łagów', subtitle: 'Zamek Joannitów i dwa jeziora', category: 'heritage', image: '/images/lagow.webp', lat: 52.3347, lng: 15.2922, rating: 4.9, location: 'Łagów', description: 'Wąski przesmyk między dwoma jeziorami, brukowane uliczki i średniowieczny zamek. W Łagowie najlepiej zwolnić tempo, wejść na wieżę i znaleźć własne miejsce nad wodą.' },
  { id: 2, name: 'Park Mużakowski', subtitle: 'Krajobraz bez granic · UNESCO', category: 'heritage', image: '/images/park.webp', lat: 51.5507, lng: 14.7357, rating: 4.8, location: 'Łęknica', description: 'Rozległe łąki, malownicze mosty i ścieżki po obu stronach Nysy Łużyckiej. Park krajobrazowy wpisany na listę UNESCO zaprasza na długi spacer.' },
  { id: 3, name: 'Międzyrzecki Rejon Umocniony', subtitle: 'Odkryj podziemną historię', category: 'heritage', image: '/images/tunnel.webp', lat: 52.3712, lng: 15.5062, rating: 4.7, location: 'Pniewo', description: 'Sieć podziemnych korytarzy i fortyfikacji tworzy niezwykły zapis historii regionu. Zwiedzanie tras podziemnych odbywa się z przewodnikiem; dostępność sprawdź przed wyjazdem.' },
  { id: 4, name: 'Smaki nad jeziorem', subtitle: 'Regionalna kuchnia z widokiem', category: 'food', image: '/images/food.webp', lat: 52.3321, lng: 15.2915, rating: 4.6, location: 'Okolice Łagowa', description: 'Inspiracja na przerwę w podróży: lokalne smaki i spokojny obiad nad wodą. To propozycja kulinarna, a nie wskazanie konkretnej restauracji.' },
  { id: 5, name: 'Jezioro Trześniowskie', subtitle: 'Czysta woda, cisza i las', category: 'nature', image: '/images/lake.webp', lat: 52.3511, lng: 15.2973, rating: 4.8, location: 'Łagów', description: 'Otoczone lasem jezioro zachęca do odpoczynku i spacerów. Z nadbrzeżnych ścieżek otwierają się piękne widoki na wodę i zielone wzgórza.' },
  { id: 6, name: 'Ujście Warty', subtitle: 'Tam, gdzie natura ma głos', category: 'nature', image: '/images/warta.webp', lat: 52.5712, lng: 14.7974, rating: 4.9, location: 'Chyrzyno', description: 'Rozlewiska, otwarta przestrzeń i świat ptaków. Zabierz lornetkę i odkrywaj park narodowy po udostępnionych ścieżkach, z szacunkiem dla przyrody.' },
]
export const trails = [
 { id: 'lakes', name: 'Wokół jezior łagowskich', type: 'bike', image: '/images/bike.webp', distance: 32, time: '3–4 h', difficulty: 'Łatwa', ids: [1,5,4] },
 { id: 'parks', name: 'Ścieżkami Parku Mużakowskiego', type: 'walk', image: '/images/park-trail.webp', distance: 18, time: '4–5 h', difficulty: 'Średnia', ids: [2] },
 { id: 'warta', name: 'W krainie Ujścia Warty', type: 'bike', image: '/images/warta.webp', distance: 46, time: '5–6 h', difficulty: 'Średnia', ids: [6] },
]
