<script>
    const buttons = document.querySelectorAll('[id^="block-btn-"]');
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            const email = button.id.substring(11);
            const url = `/block-user?email=${email}`;
            fetch(url)
                .then(response => response.json())
                .then(data => {

                })
                .catch(error => {
                });
        });
    });
</script>
