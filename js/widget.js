import * as wwt from '@wwtelescope/engine';
import { wwt_apply_json_message } from './wwt_json_api';
import "./widget.css";


async function render({model, el}) {
    // Create a unique ID for the container
    const containerId = `wwt-container-${Math.random().toString(36).substr(2, 9)}`;

    // Create container and canvas with the unique ID
    const container = document.createElement('div');
    container.id = containerId;
    container.classList.add('wwt-widget');
    container.style.height = "500px";
    container.style.widget = "100%";
    el.appendChild(container);

    // Initialize WWT engine
    const builder = new wwt.WWTControlBuilder(containerId);
    builder.startRenderLoop(true);
    const scriptInterface = builder.create();
    const control = wwt.WWTControl.singleton;
    const wwtSettings = scriptInterface.settings;

    // Set the model to ready
    scriptInterface.add_ready(() => {
        console.log("WWT ready");
        model.set("_wwt_ready", true);
        model.save_changes();
    });

    // Handle commands
    model.on("change:_commands", () => {
        const commands = model.get("_commands");

        model.set("_dirty", true);
        model.save_changes();

        commands.forEach(cmd => {
            wwt_apply_json_message(control, wwt, scriptInterface, wwtSettings, cmd);
        });

        // Clear processed commands
        console.log('clearing commands');
    });
}

export default { render };