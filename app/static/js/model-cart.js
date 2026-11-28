(() => {
    const link = document.getElementById('model-cart-link');
    const count = document.getElementById('model-cart-count');
    const selector = '[data-model-cart-id]';
    let selected = null;
    let busy = false;

    function updateButtons() {
        document.querySelectorAll(selector).forEach(button => {
            const inCart = selected?.has(Number(button.dataset.modelCartId));
            const row = button.closest('[data-model-cart-row]');
            if (row && selected && !inCart) {
                row.remove();
                return;
            }
            button.textContent = inCart ? 'Remove from cart' : 'Add to cart';
            button.disabled = selected === null || busy;
        });
    }

    async function loadCart(url, options) {
        const response = await fetch(url, options);
        if (!response.ok) throw new Error('Could not load the model cart');
        const { ids } = await response.json();
        selected = new Set(ids);
        count.textContent = ids.length;
        updateButtons();

        const empty = document.getElementById('model-cart-empty');
        if (empty) {
            empty.hidden = ids.length > 0;
            document.getElementById('model-cart-download').hidden = ids.length === 0;
        }
    }

    document.addEventListener('click', async event => {
        const button = event.target.closest(selector);
        if (!button || !selected || busy) return;

        const id = Number(button.dataset.modelCartId);
        busy = true;
        updateButtons();
        try {
            await loadCart(link.dataset.updateUrl.replace(/0$/, id), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ in_cart: !selected.has(id) }),
            });
        } catch {
            window.alert('Could not update the cart. Refresh the page and try again.');
        } finally {
            busy = false;
            updateButtons();
        }
    });

    const observer = new MutationObserver(updateButtons);
    const results = document.getElementById('results-container');
    const workbenchButton = document.getElementById('workbench-cart-button');
    if (results) observer.observe(results, { childList: true });
    if (workbenchButton) observer.observe(workbenchButton, { attributeFilter: ['data-model-cart-id'] });

    const refresh = () => loadCart(link.dataset.itemsUrl).catch(() => {
        count.textContent = '';
        selected = null;
        updateButtons();
    });
    refresh();
    window.addEventListener('pageshow', event => {
        if (event.persisted) refresh();
    });
})();
