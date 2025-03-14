import "./widget.css";


async function render({model, el}) {
    // Create a unique ID for the container
    const containerId = `wwt-container-${Math.random().toString(36).substr(2, 9)}`;
    const serverUrl = model.get("server_url");
    const serverOrigin = new URL(serverUrl).origin;

    let _alive = false;
    let _lastPongTimestamp = 0;

    // Create iframe
    const iframe = document.createElement('iframe');
    // iframe.src = 'https://web.wwtassets.org/research/latest/?origin=' + location.origin;
    iframe.src = serverUrl + "/research/?origin=" + location.origin;
    iframe.style.width = "100%";
    iframe.style.height = "400px";
    iframe.style.border = "none";
    iframe.id = containerId;

    el.appendChild(iframe);

    window.addEventListener(
        'message',
        function (event) { processDomWindowMessage(event); },
        false
    );

    setInterval(function () { checkApp(); }, 1000);

    function processDomWindowMessage(event) {
        const payload = event.data;
        if (event.origin !== serverOrigin)
            return;

        if (payload.type === "wwt_ping_pong" && payload.sessionId === containerId) {
            const ts = +payload.threadId;

            if (!isNaN(ts)) {
                _lastPongTimestamp = ts;
            }
        } else {
            model.send(payload);
        }
    }

    function checkApp() {
        const window = iframe.contentWindow;

        if (window) {
            window.postMessage({
                type: "wwt_ping_pong",
                threadId: "" + Date.now(),
                sessionId: containerId,
            }, serverOrigin);
        }
        _alive = (Date.now() - _lastPongTimestamp) < 2500;

        if (_alive && !model.get("_wwt_ready")) {
            console.log("WWT research app is ready!");
            model.set("_wwt_ready", true);
            model.save_changes();
        }
    }

    // Handle commands
    model.on("change:_commands", () => {
        const commands = model.get("_commands");

        model.set("_dirty", true);
        model.save_changes();

        commands.forEach(cmd => {
            const window = iframe.contentWindow;

            if (window) {
                window.postMessage(cmd, serverOrigin);
            }
        });
    });
}

export default {render};