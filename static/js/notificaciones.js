const btnNotificaciones =
    document.getElementById('btnNotificaciones');

const modalNotificaciones =
    document.getElementById('modalNotificaciones');

const cerrarNotificaciones =
    document.getElementById('cerrarNotificaciones');

const contenedorNotificaciones =
    document.getElementById('contenedorNotificaciones');


// ABRIR MODAL

btnNotificaciones.addEventListener('click', async () => {

    modalNotificaciones.classList.remove('hidden');

    await cargarNotificaciones();

});


// CERRAR MODAL

cerrarNotificaciones.addEventListener('click', () => {

    modalNotificaciones.classList.add('hidden');

});


// CARGAR NOTIFICACIONES


async function cargarNotificaciones() {

    try {

        const response = await fetch('/api/notificaciones');
        const data = await response.json();

        const notificaciones = (Array.isArray(data) ? data : []).filter(n =>
            String(n.tipo || '').toUpperCase() === 'INTERNA'
        );

        if (notificaciones.length === 0) {
            contenedorNotificaciones.innerHTML = `
                <p class="notificacion-vacia">No tienes notificaciones.</p>
            `;
            return;
        }

        contenedorNotificaciones.innerHTML = '';

        notificaciones.forEach(n => {

            const div = document.createElement('div');

            div.className = `notificacion-card ${n.leida == 0 ? 'no-leida' : ''}`;

            div.innerHTML = `
                <div class="notificacion-header">
                    <span class="notificacion-titulo">Notificación </span>
                    <span class="notificacion-fecha">${n.fecha_envio}</span>
                </div>
                <div class="notificacion-mensaje">
                    ${n.mensaje}
                </div>
            `;

            contenedorNotificaciones.appendChild(div);

            // Marcar como leída automáticamente
            if (n.leida == 0) {
                fetch(`/api/notificaciones/${n.id_notificacion}/leer`, {
                    method: 'PUT'
                }).catch(() => { });
            }

        });

    } catch (error) {

        contenedorNotificaciones.innerHTML = `
            <p class="notificacion-vacia">Error cargando notificaciones</p>
        `;

    }

}