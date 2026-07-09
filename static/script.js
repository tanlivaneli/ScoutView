function showSearch(type) {
    document.getElementById('team-search').style.display = type === 'team' ? 'block' : 'none';
    document.getElementById('player-search').style.display = type === 'player' ? 'block' : 'none';

    document.querySelectorAll('.search-tab').forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
}