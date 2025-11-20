# Iterate over all gpx files in the tracks folder and plot the elevation profile
import os
import math
import gpxpy
import svgwrite
import matplotlib.pyplot as plt
import yaml

# Load configuration
with open('config.yaml', 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)

def generate_elevation_profile():
    elevations = []
    distances = []
    stops = []
    total_distance = 0
    for filename in sorted(os.listdir(cfg['track_folder'])):
        if filename.endswith('.gpx'):
            file_path = os.path.join(cfg['track_folder'], filename)
            with open(file_path, 'r', encoding='utf-8') as gpx_file:
                gpx = gpxpy.parse(gpx_file) 

                for track in gpx.tracks:
                    for segment in track.segments:
                        previous_point = None
                        for point in segment.points:
                            elevations.append(point.elevation)
                            # for each first point set the stop name, for others set empty string
                            if previous_point is None:
                                stop_name = os.path.splitext(filename)[0]
                                stops.append(stop_name)
                            else:
                                stops.append("")
                            if previous_point is not None:
                                distance = point.distance_3d(previous_point)
                                total_distance += distance
                            distances.append(total_distance)
                            previous_point = point
                print(f'Processed {filename}, total distance so far: {total_distance} m')

    ## Plot the combined elevation profile
    print('Plotting combined elevation profile for all GPX tracks...')
    print(f'Total distance: {total_distance} m, Total elevation points: {len(elevations)}')
    plt.figure()
    plt.plot(distances, elevations)
    plt.title(f'Elevation Profile for all GPX Tracks')
    plt.xlabel('Distance (m)')
    plt.ylabel('Elevation (m)')
    plt.grid()
    plt.savefig(cfg['elevation_plot_file'])
    plt.close()
    return distances, elevations, stops

def generate_svg_elevation_profile(distances, elevations, stops_keys, stop_metadata):
    # Generate svg file for the elevation profile

    canvas_size = (cfg['canvas_width'], cfg['canvas_height'])
    print('Generating SVG for elevation profile...')
    dwg = svgwrite.Drawing('out/design.svg', profile='full', size=canvas_size)
    dwg['style'] = "background: none;"

    # Special drawing instructions:
    # In the center of the canvas draw a circle with a radius of `circle_radius` and fill it with a center image
    dwg.add(dwg.circle(center=(canvas_size[0] / 2, canvas_size[1] / 2), r=cfg['circle_radius']+cfg['line_size'], stroke='black', stroke_width=cfg['line_size']))
    # Add the image to the center and clip it to the circle
    dwg.add(dwg.image(cfg['center_image_path'], insert=(canvas_size[0] / 2 - cfg['circle_radius'], canvas_size[1] / 2 - cfg['circle_radius']), size=(cfg['circle_radius'] * 2, cfg['circle_radius'] * 2)))
    
    # Draw elevation profile as a circular line around the center circle
    max_distance = max(distances)
    max_elevation = max(elevations)
    min_elevation = min(elevations)
    num_points = len(distances)
    print(f'Max distance: {max_distance}, Max elevation: {max_elevation}, Min elevation: {min_elevation}, Num points: {num_points}')
    # Stop marker list
    stops = []
    
    for i in range(num_points - 1):
        angle1 = (distances[i] / max_distance) * 360 + cfg['start_angle']
        angle2 = (distances[i + 1] / max_distance) * 360 + cfg['start_angle']
        radius1 = cfg['circle_radius'] + ((elevations[i] - min_elevation) / (max_elevation - min_elevation)) * (canvas_size[0] / 2 - cfg['circle_radius'] - cfg['padding_outside']) + cfg['padding_inside']
        radius2 = cfg['circle_radius'] + ((elevations[i + 1] - min_elevation) / (max_elevation - min_elevation)) * (canvas_size[0] / 2 - cfg['circle_radius'] - cfg['padding_outside']) + cfg['padding_inside']
        x1 = canvas_size[0] / 2 + radius1 * math.cos(math.radians(angle1))
        y1 = canvas_size[1] / 2 + radius1 * math.sin(math.radians(angle1))
        x2 = canvas_size[0] / 2 + radius2 * math.cos(math.radians(angle2))
        y2 = canvas_size[1] / 2 + radius2 * math.sin(math.radians(angle2))
        y2 = canvas_size[1] / 2 + radius2 * math.sin(math.radians(angle2))

        # If there is a stop at this point, draw a circle marker with text indicating the stop name
        if stops_keys[i] and stops_keys[i] in stop_metadata and stop_metadata[stops_keys[i]]['show']:
            text_angle = stop_metadata[stops_keys[i]]['angle']
            text_invert = stop_metadata[stops_keys[i]]['invert_text']
            text_anchor = 'start'
            stop_circle = dwg.circle(center=(x1, y1), r=3*cfg['line_size'], fill='white', stroke='black', stroke_width=cfg['line_size'])
            text_offset_x = 5 * cfg['line_size'] * math.cos(math.radians(text_angle))
            text_offset_y = 5 * cfg['line_size'] * math.sin(math.radians(text_angle))
            # Calculate rotation angle so text faces away from the track line
            if text_invert:
                text_angle += 180
                text_anchor = 'end'
            stop_text = dwg.text(
                stop_metadata[stops_keys[i]]['display_name'],
                insert=(x1 + text_offset_x, y1 + text_offset_y),
                font_size=6*cfg['line_size'],
                fill=cfg['stop_text_color'],
                font_family=cfg['font_family'],
                text_anchor=text_anchor,
                transform=f"rotate({text_angle},{x1 + text_offset_x},{y1 + text_offset_y})"
            )
            stops.append((stop_circle, stop_text))
        # Draw line segment
        # Smooth the path by reducing the point count
        step = max(1, num_points // 700)  # target ~500 points for smoothness
        if i % step == 0:
            if i == 0:
                path_d = f"M{x1},{y1} "
            else:
                path_d += f"L{x2},{y2} "
    # After the loop, add the path to the drawing
    dwg.add(dwg.path(d=path_d, stroke=cfg['line_color'], stroke_width=cfg['line_size'], fill='none'))
    
    # Add stop markers to the drawing
    for stop_circle, stop_text in stops:
        dwg.add(stop_circle)
        dwg.add(stop_text)
    
    # Bend the heading along a circular path around the inner circle
    cx = canvas_size[0] / 2
    cy = canvas_size[1] / 2
    text_radius = cfg['circle_radius'] + cfg['padding_inside'] + cfg['padding_outside']  # radius for the text path
    # Embed custom font
    # dwg.embed_font(name="Aniron", filename="fonts/Aniron/Aniron-7BaP.ttf")

    # Add bold heading font above the circle
    path_heading_id = 'headingPath'
    path_heading = (
        f"M{cx},{cy} m {text_radius},0 "
        f"a {text_radius},{text_radius} 0 1,1 -{text_radius*2},0 "
        f"a {text_radius},{text_radius} 0 1,1 {text_radius*2},0"
    )
    dwg.defs.add(dwg.path(d=path_heading, id=path_heading_id, fill='none'))
    text_heading = dwg.text(
        '', 
        fill=cfg['heading_color'], 
        font_size=cfg['heading_font_size'], 
        font_weight='bold', 
        font_family=cfg['font_family']
    )
    text_heading.add(dwg.textPath(f'#{path_heading_id}', cfg['heading_text'], startOffset=cfg['heading_rotation']))
    dwg.add(text_heading)
    # Add foot heading font below the circle
    path_footer_id = 'footerPath'
    path_footer = (
        f"M{cx},{cy} m -{text_radius},0 "
        f"a {text_radius},{text_radius} 0 1,0 {text_radius*2},0 "
        f"a {text_radius},{text_radius} 0 1,0 -{text_radius*2},0"
    )
    dwg.defs.add(dwg.path(d=path_footer, id=path_footer_id, fill='none'))
    text_footer = dwg.text(
        '',
        fill=cfg['footer_color'],
        font_size=cfg['footer_font_size'],
        font_weight='bold',
        style="text-anchor:middle",
        font_family=cfg['font_family']
    )
    text_footer.add(dwg.textPath(f'#{path_footer_id}', cfg['footer_text'], startOffset=cfg['footer_rotation']))
    dwg.add(text_footer)
    # export the canvas to svg file
    dwg.save(pretty=True)

def get_elevation_data(debug=False):
    if debug:
        distances = [1]
        elevations = [2]
        stops = ['test']
    elif os.path.exists(cfg['elevation_data']):
        print('Loading pre-calculated elevation profile from CSV...')
        distances = []
        elevations = []
        stops = []
        with open(cfg['elevation_data'], 'r', encoding='utf-8') as f:
            next(f)  # skip header
            for line in f:
                d, e, s = line.strip().split(',')
                distances.append(float(d))
                elevations.append(float(e))
                stops.append(s)
        print(f'Loaded {len(distances)} points from CSV.')
    else:
        distances, elevations, stops = generate_elevation_profile()
        assert len(distances) == len(elevations) == len(stops)
        # store the calculated distances and elevations to a csv file
        with open(cfg['elevation_data'], 'w', encoding='utf-8') as f:
            f.write('Distance(m),Elevation(m),Stops\n')
            for d, e, s in zip(distances, elevations, stops):
                f.write(f'{d},{e},{s}\n')
        # write the stops to a metadata csv file if not already existing
        if not os.path.exists(cfg['metadata_file']):
            print('Writing stops metadata to CSV...')
            with open(cfg['metadata_file'], 'w', encoding='utf-8') as f:
                f.write('show,stop_key,display_name,invert_text,angle\n')
                for stop in sorted(set(stops)):
                    if stop:  # only write non-empty stops
                        f.write(f'True,{stop},{stop},False,0\n')
    return distances,elevations,stops

def get_metadata():
    stop_metadata = {}
    if os.path.exists(cfg['metadata_file']):
        print('Loading stop metadata from CSV...')
        with open(cfg['metadata_file'], 'r', encoding='utf-8') as f:
            next(f)  # skip header
            for line in f:
                show, stop_key, display_name, invert_text, angle = line.strip().split(',')
                stop_metadata[stop_key] = {
                    'show': show.lower() == 'true',
                    'display_name': display_name,
                    'invert_text': invert_text.lower() == 'true',
                    'angle': float(angle)
                }
        print(f'Loaded metadata for {len(stop_metadata)} stops.')
    else:
        raise FileNotFoundError(f'Metadata file {cfg["metadata_file"]} not found, rebuild elevation data to create it.')
    return stop_metadata

if __name__ == '__main__':
    # Create output folder if it doesn't exist
    if not os.path.exists('out'):
        os.makedirs('out')
    distances, elevations, stops = get_elevation_data()
    metadata = get_metadata()
    generate_svg_elevation_profile(distances, elevations, stops, metadata)