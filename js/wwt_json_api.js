// This file is a mini-library that translates JSON messages into actions
// on the WWT side. The reason for having this in its own file is that
// we can then use it for both the Jupyter widget and other front-ends such
// as the Qt one.


var ReferenceFramesRadius = {
  Sky: 149500000000,
  Sun: 696000000,
  Mercury: 2439700,
  Venus: 6051800,
  Earth: 6371000,
  Mars: 3390000,
  Jupiter: 69911000,
  Saturn: 58232000,
  Uranus: 25362000,
  Neptune: 24622000,
  Pluto: 1161000,
  Moon: 1737100,
  Io: 1821500,
  Europa: 1561000,
  Ganymede: 2631200,
  Callisto: 2410300
};

export function wwt_apply_json_message(control, wwt, scriptInterface, wwtSettings, msg) {
  if (!control.hasOwnProperty('annotations')) {
    control.annotations = {};
    control.layers = {};
  }

  switch(msg['event']) {

    case 'clear_annotations':
      return control.clearAnnotations();
      break;

    case 'get_datetime':
      return wwt.SpaceTimeController.get_now().toISOString();
      break;

    case 'get_dec':
      return control.getDec();
      break;

    case 'get_ra':
      return control.getRA();
      break;

    case 'get_fov':
      return control.get_fov();
      break;

    case 'load_tour':
      control.loadTour(msg['url']);
      break;

    case 'resume_tour':
      control.playTour();
      break;

    case 'pause_tour':
      control.stopTour();
      break;

    case 'resume_time':
      wwt.SpaceTimeController.set_syncToClock(true);
      wwt.SpaceTimeController.set_timeRate(msg['rate']);
      break;

    case 'pause_time':
      wwt.SpaceTimeController.set_syncToClock(false);
      break;

    case 'load_image_collection':
      scriptInterface.loadImageCollection(msg['url']);
      break;

    case 'set_foreground_by_name':
      control.setForegroundImageByName(msg['name']);
      break;

    case 'set_background_by_name':
      control.setBackgroundImageByName(msg['name']);
      break;

    case 'set_foreground_opacity':
      scriptInterface.setForegroundOpacity(msg['value']);
      break;

    case 'center_on_coordinates':
      control.gotoRADecZoom(msg['ra'], msg['dec'], msg['fov'], msg['instant']);
      break;

    case 'setting_set':
      var name = msg['setting'];
      wwtSettings["set_" + name](msg['value']);
      break;

    case 'annotation_create':

      switch(msg['shape']) {
        case 'circle':
          // TODO: check if ID already exists
          let circle = control.createCircle();
          circle.set_id(msg['id']);
          circle.set_skyRelative(true);
          circle.setCenter(control.getRA() * 15, control.getDec());
          control.addAnnotation(circle);
          control.annotations[msg['id']] = circle;
          break;

        case 'polygon':
          // same TODO as above
          let polygon = control.createPolygon();
          polygon.set_id(msg['id']);
          control.addAnnotation(polygon);
          control.annotations[msg['id']] = polygon;
          break;

        case 'line':
          // same TODO as above
          let line = control.createPolyLine();
          line.set_id(msg['id']);
          control.addAnnotation(line);
          control.annotations[msg['id']] = line;
          break;
      }
      break;

    case 'annotation_set':
      var name = msg['setting'];
      // TODO: nice error message if annotation doesn't exist
      let annotation = control.annotations[msg['id']];
      annotation["set_" + name](msg['value']);
      break;

    case 'remove_annotation':
      var name = msg["setting"];
      // TODO: nice error message if annotation doesn't exist
      let shape = control.annotations[msg['id']];
      control.removeAnnotation(shape);
      break;

    case 'circle_set_center':
      var name = msg["setting"];
      // TODO: nice error message if annotation doesn't exist
      let circle = control.annotations[msg['id']];
      circle.setCenter(msg['ra'], msg['dec']);
      break;

    case 'polygon_add_point':
      var name = msg["setting"];
      // same TODO as above
      let polygon = control.annotations[msg['id']];
      polygon.addPoint(msg['ra'], msg['dec']);
      break;

    case 'line_add_point':
      var name = msg["setting"];
      // same TODO as above
      let line = control.annotations[msg['id']];
      line.addPoint(msg['ra'], msg['dec']);
      break;

    case 'set_datetime':
      var date = new Date(msg['isot']);
      let stc = wwt.SpaceTimeController;
      stc.set_timeRate(1);
      stc.set_now(date);
      break;

    case 'set_viewer_mode':
      // We need to set both the backround and foreground layers
      // otherwise when changing to planet view, there are weird
      // artifacts due to the fact one of the layers is the sky.
      control.setBackgroundImageByName(msg['mode']);
      control.setForegroundImageByName(msg['mode']);
      break;

    case 'track_object':
      wwt.WWTControl.singleton.renderContext.set_solarSystemTrack(msg['code']);
      break;

    case 'image_layer_create':
      layer = control.loadFits(msg['url']);
      layer._stretch_version = 0;
      layer._cmap_version = 0;
      control.layers[msg['id']] = layer;
      break;

    case 'image_layer_stretch':
      var layer = control.layers[msg['id']];

      if (layer.get_imageSet() == null) {

        // When the image layer is created, the image is not immediately available.
        // If the stretch is modified before the image layer is available, we
        // call the wwt_apply_json_message function again at some small time
        // interval in the future.

        setTimeout(function(){ wwt_apply_json_message(control, msg); }, 200);

      } else {

        // Once we get here, the image has downloaded. If we are in a deferred
        // call, we want to only apply the call if the version of the call
        // is more recent than the currently set version. We do this check
        // because there is no guarantee that the messages arrive in the right
        // order.

        if (msg['version'] > layer._stretch_version) {
          layer.setImageScalePhysical(msg['stretch'], msg['vmin'], msg['vmax']);
          layer._stretch_version = msg['version'];

          // old transparentBlack API, @wwtelescope/engine <= 7.10. With
          // newer engines, this is a harmless no-op.
          layer.getFitsImage().transparentBlack = false;

          // new transparentBlack API
          var imageset = layer.get_imageSet();
          if (typeof imageset['get_fitsProperties'] !== 'undefined') {
              imageset.get_fitsProperties().transparentBlack = false;
          }
        }

      }
      break;

    case 'image_layer_cmap':
      // See image_layer_stretch for why we need to do what we do below
      var layer = control.layers[msg['id']];

      if (layer.get_imageSet() == null) {
        setTimeout(function(){ wwt_apply_json_message(control, msg); }, 200);
      } else {
        if (msg['version'] > layer._cmap_version) {
          layer.set_colorMapperName(msg['cmap']);
          layer._cmap_version = msg['version'];
        }
      }
      break;

    case 'image_layer_set':
      var layer = control.layers[msg['id']];
      var name = msg['setting'];
      layer["set_" + name](msg['value']);
      break;

    case 'image_layer_remove':
      // TODO: could combine with table_layer_remove
      var layer = control.layers[msg['id']];
      wwt.LayerManager.deleteLayerByID(layer.id, true, true);
      break;

    case 'table_layer_create':
      // Decode table from base64
      let csv = atob(msg['table'])

      // Get reference frame
      let frame = msg['frame']

      layer = wwt.LayerManager.createSpreadsheetLayer(frame, 'PyWWT Layer', csv);
      layer.set_referenceFrame(frame);

      // Override any guesses
      layer.set_lngColumn(-1);
      layer.set_latColumn(-1);
      layer.set_altColumn(-1);
      layer.set_sizeColumn(-1);
      layer.set_colorMapColumn(-1);
      layer.set_startDateColumn(-1);
      layer.set_endDateColumn(-1);
      layer.set_xAxisColumn(-1);
      layer.set_yAxisColumn(-1);
      layer.set_zAxisColumn(-1);

      // FIXME: at the moment WWT incorrectly sets the mean radius of the object
      // in the frame to that of the Earth, so we need to override this here.
      let radius = ReferenceFramesRadius[frame];
      if (radius != undefined) {
        layer._meanRadius$1 = radius;
      }

      // FIXME: for now, this doesn't have any effect because WWT should add a 180
      // degree offset but it doesn't - see
      // https://github.com/WorldWideTelescope/wwt-web-client/pull/182 for a
      // possible fix.
      if (frame == 'Sky') {
        layer.set_astronomical(true);
      }

      layer.set_altUnit(1);

      control.layers[msg['id']] = layer;
      break;

    case 'table_layer_update':
      var layer = control.layers[msg['id']];

      // Decode table from base64
      csv = atob(msg['table']);

      // Use updateData instead of loadFromString here since updateData also
      // takes care of cache invalidation.
      layer.updateData(csv, true, true, true)

      break;

    case 'table_layer_set':
      var layer = control.layers[msg['id']];
      var name = msg['setting'];
      var value = null;

      //if (name.includes('Column')) { // compatability issues?
      if (name.indexOf('Column') >= 0) {
        value = layer.get__table().header.indexOf(msg['value']);
      } else if(name == 'color') {
        value = wwt.Color.fromHex(msg['value']);
      } else if(name == 'colorMapper') {
        value = wwt.ColorMapContainer.fromArgbList(msg['value']);
      } else if(name == 'altUnit') {
        value = wwt.AltUnits[msg['value']];
      } else if(name == 'raUnits') {
        value = wwt.RAUnits[msg['value']];
      } else if(name == 'altType') {
        value = wwt.AltTypes[msg['value']];
      } else if(name == 'plotType') {
        value = wwt.PlotTypes[msg['value']];
      } else if(name == 'markerScale') {
        value = wwt.MarkerScales[msg['value']];
      } else if(name == 'coordinatesType') {
        value = wwt.CoordinatesTypes[msg['value']];
      } else if(name == 'cartesianScale') {
        value = wwt.AltUnits[msg['value']];
      } else {
        value = msg['value']
      }
      layer["set_" + name](value);
      break;

    case 'table_layer_remove':
      var layer = control.layers[msg['id']];
      wwt.LayerManager.deleteLayerByID(layer.id, true, true);
      break;
  }
}

// We need to do this so that wwt_apply_json_message is available as a global
// function in the Jupyter widgets code.
// window.wwt_apply_json_message = wwt_apply_json_message;