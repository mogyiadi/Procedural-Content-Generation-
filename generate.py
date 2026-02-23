import sys
import math
import random
from gdpc import Editor, Block

editor = Editor(buffering=True)

# picks random block for walls
def get_random_wall_block():
    blocks = [
        "stone_bricks", "stone_bricks", "stone_bricks",
        "cobblestone", "cobblestone",
        "mossy_cobblestone", "mossy_stone_bricks",
        "cracked_stone_bricks"
    ]
    
    # 10 percent chance for stairs to add detail
    if random.random() < 0.10:
        dirs = ["north", "south", "east", "west"]
        halfs = ["bottom", "top"]
        mat = random.choice(['stone_brick', 'cobblestone'])
        return Block(mat + "_stairs", {"facing": random.choice(dirs), "half": random.choice(halfs)})
        
    return Block(random.choice(blocks))

# gets roof block for towers
def get_random_roof_block():
    roof_blocks = ["deepslate_tiles", "deepslate_bricks", "cobbled_deepslate"]
    return Block(random.choice(roof_blocks))

# checks if window goes here
def is_window_column(dx, dz):
    if dz == -20 and dx % 5 == 0 and abs(dx) < 23: 
        return True
    if dz == 0 and dx % 5 == 0 and 12 < abs(dx) < 23: 
        return True
    if abs(dx) == 25 and dz % 5 == 0 and -18 < dz < -2: 
        return True
    if abs(dx) == 10 and dz % 5 == 0 and 2 < dz < 28: 
        return True
    if dz == 30 and abs(dx) == 7: 
        return True
    return False

# finds wood and floor types
def get_biome_info(editor, x, y, z):
    wood_type = "oak"
    ground = ["dirt_path", "coarse_dirt", "cobblestone"]
    
    try:
        b = editor.getBiome((x, y, z))
        if b != None:
            b = b.lower()
            if "taiga" in b or "snow" in b or "pine" in b:
                wood_type = "spruce"
                ground = ["podzol", "coarse_dirt"]
            elif "birch" in b:
                wood_type = "birch"
            elif "jungle" in b or "bamboo" in b:
                wood_type = "jungle"
                ground = ["moss_block", "coarse_dirt"]
            elif "savanna" in b:
                wood_type = "acacia"
            elif "dark" in b or "roofed" in b:
                wood_type = "dark_oak"
            elif "cherry" in b:
                wood_type = "cherry"
            elif "mangrove" in b or "swamp" in b:
                wood_type = "mangrove"
                ground = ["mud", "packed_mud"]
            elif "desert" in b or "badlands" in b:
                ground = ["smooth_sandstone", "gravel"]
    except:
        pass # just use oak if it fails
        
    return wood_type, ground

# builds small hut or deposit
def build_hut(local_x, y, local_z, h_type, wood, editor):
    # clear space first
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            for dy in range(1, 5):
                editor.placeBlock((local_x + dx, y + dy, local_z + dz), Block("air"))
    
    if h_type == "blacksmith":
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                editor.placeBlock((local_x + dx, y, local_z + dz), Block("cobblestone"))
                editor.placeBlock((local_x + dx, y + 4, local_z + dz), Block("cobblestone_slab"))
                
        for dx, dz in [(-2,-2), (2,-2), (-2,2), (2,2)]:
            for dy in range(1, 4):
                editor.placeBlock((local_x + dx, y + dy, local_z + dz), Block(f"{wood}_log", {"axis": "y"}))
                
        editor.placeBlock((local_x, y + 1, local_z), Block("anvil"))
        editor.placeBlock((local_x + 1, y + 1, local_z + 1), Block("furnace", {"facing": "north"}))
        editor.placeBlock((local_x - 1, y + 1, local_z - 1), Block("lava_cauldron"))
        
    elif h_type == "merchant":
        colors = ["red", "blue", "yellow", "green", "white"]
        c = random.choice(colors)
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                editor.placeBlock((local_x + dx, y, local_z + dz), Block(f"{wood}_planks"))
                editor.placeBlock((local_x + dx, y + 3, local_z + dz), Block(f"{c}_wool"))
                
        for dx, dz in [(-2,-2), (2,-2), (-2,2), (2,2)]:
            for dy in range(1, 3):
                editor.placeBlock((local_x + dx, y + dy, local_z + dz), Block(f"{wood}_fence"))
                
        editor.placeBlock((local_x, y + 1, local_z), Block("barrel", {"facing": "up"}))
        editor.placeBlock((local_x + 1, y + 1, local_z), Block("chest", {"facing": "north"}))
        
    elif h_type == "hay":
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                editor.placeBlock((local_x + dx, y, local_z + dz), Block("dirt_path"))
        editor.placeBlock((local_x, y + 1, local_z), Block("hay_block", {"axis": "y"}))
        editor.placeBlock((local_x + 1, y + 1, local_z), Block("hay_block", {"axis": "x"}))
        editor.placeBlock((local_x, y + 2, local_z), Block("hay_block", {"axis": "y"}))
        editor.placeBlock((local_x - 1, y + 1, local_z), Block("composter"))

    elif h_type in ["coal_deposit", "iron_deposit", "copper_deposit"]:
        if h_type == "coal_deposit":
            ore = "coal_block"
        elif h_type == "iron_deposit":
            ore = "raw_iron_block"
        else:
            ore = "raw_copper_block"
            
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                editor.placeBlock((local_x + dx, y, local_z + dz), Block("cobblestone"))
                if random.random() < 0.6: 
                    editor.placeBlock((local_x + dx, y + 1, local_z + dz), Block(ore))
        editor.placeBlock((local_x, y + 2, local_z), Block(ore))

# checks if inside keep bounds
def is_inside(dx, dz):
    rec1 = (-25 <= dx <= 25) and (-20 <= dz <= 0)
    rec2 = (-10 <= dx <= 10) and (0 < dz <= 30)
    if rec1 or rec2:
        return True
    return False

# checks if block is wall
def is_wall(dx, dz):
    if not is_inside(dx, dz): 
        return False
    # check neighbours
    if not is_inside(dx+1, dz) or not is_inside(dx-1, dz) or not is_inside(dx, dz+1) or not is_inside(dx, dz-1): 
        return True
    return False

# checks if block is stairs
def is_stairs(dx, dz):
    # Main stair run (South from keep)
    if -2 <= dx <= 2 and 31 <= dz <= 37:
        return True
    # Lower run (West towards ground)
    if -15 <= dx <= 2 and 37 <= dz <= 40:
        return True
    return False

# main function to build castle
def build_castle():
    buildArea = editor.getBuildArea()
    worldSlice = editor.loadWorldSlice(buildArea.toRect(), cache=True)
    heightmap = worldSlice.heightmaps["MOTION_BLOCKING_NO_LEAVES"]
    
    # find the middle
    cx = buildArea.begin.x + buildArea.size.x // 2
    cz = buildArea.begin.z + buildArea.size.z // 2
    center_y = int(heightmap[cx - buildArea.begin.x][cz - buildArea.begin.z])
    
    keep_base_y = center_y + 10 # elevated
    wood, ground_textures = get_biome_info(editor, cx, center_y, cz)
    print("biome wood is:", wood)

    radius = 49 
    wall_height = 14 
    
    perimeter_points = []
    for angle in range(360):
        rad = math.radians(angle)
        x_pos = int(cx + radius * math.cos(rad))
        z_pos = int(cz + radius * math.sin(rad))
        if (x_pos, z_pos) not in perimeter_points:
            perimeter_points.append((x_pos, z_pos))
        
    # sort so it draws in a circle smoothly
    perimeter_points.sort(key=lambda p: math.atan2(p[1] - cz, p[0] - cx))
    
    prev_y = None
    wall_bases = []
    perimeter_set = set(perimeter_points)  # for fast lookup when checking surrounding heights

    print("calculating wall heights...")
    for p in perimeter_points:
        x = p[0]
        z = p[1]
        hx = x - buildArea.begin.x
        hz = z - buildArea.begin.z
        
        # bounds check
        if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:
            ground_y = int(heightmap[hx][hz])
            
            # drill down if we hit a tree (logs/leaves) to find actual ground
            while ground_y > -64:
                block_id = worldSlice.getBlockGlobal((x, ground_y, z)).id
                if "log" in block_id or "leaves" in block_id or "vine" in block_id or "water" in block_id:
                    ground_y -= 1
                else:
                    break
        else:
            ground_y = 64
            
        base_y = ground_y

        # Make walls taller if next to a cliff
        max_surrounding_y = ground_y
        angle = math.atan2(z - cz, x - cx)
        for out_dist in range(1, 9):
            ox = int(x + out_dist * math.cos(angle))
            oz = int(z + out_dist * math.sin(angle))
            ohx = ox - buildArea.begin.x
            ohz = oz - buildArea.begin.z
            # Skip if this point is on the wall perimeter itself
            if (ox, oz) in perimeter_set:
                continue
            if 0 <= ohx < buildArea.size.x and 0 <= ohz < buildArea.size.z:
                out_y = int(heightmap[ohx][ohz])
                if out_y > max_surrounding_y:
                    max_surrounding_y = out_y

        # Ensure the wall is at least 10 blocks taller than the highest nearby point
        local_wall_h = max(wall_height, (max_surrounding_y - base_y) + 10)
        # -----------------------------
        
        # stop walls going too deep in ravines
        if prev_y is not None:
            if prev_y - ground_y > 10: 
                base_y = prev_y 
            elif ground_y - prev_y > 10: 
                base_y = ground_y
                
        wall_bases.append((x, base_y, z, ground_y, local_wall_h))
        prev_y = base_y
        
    gate_cx = cx
    gate_cz = cz + radius

    # Find a consistent base Y for the gate from surrounding wall points
    gate_base_y = None
    for w in wall_bases:
        if abs(w[0] - gate_cx) <= 3 and abs(w[2] - gate_cz) <= 1:
            if gate_base_y is None or w[1] < gate_base_y:
                gate_base_y = w[1]
    if gate_base_y is None:
        gate_base_y = center_y

    gate_half_w = 2     # half-width of the full gate frame
    gate_opening_w = 1  # half-width of the air opening
    gate_opening_h = 5  # height of the air opening

    print("building walls and gate...")
    for w in wall_bases:
        x = w[0]
        base_y = w[1]
        z = w[2]
        ground_y = w[3]
        curr_wall_h = w[4]

        dx_gate = x - gate_cx
        dz_gate = abs(z - gate_cz)
        is_gate_area = abs(dx_gate) <= gate_half_w and dz_gate <= 1

        if is_gate_area:
            # Use consistent base for entire gate so it forms a clean rectangle
            for y in range(gate_base_y, gate_base_y + curr_wall_h):
                if abs(dx_gate) <= gate_opening_w and y < gate_base_y + gate_opening_h:
                    editor.placeBlock((x, y, z), Block("air"))
                elif abs(dx_gate) == gate_half_w:
                    editor.placeBlock((x, y, z), Block(f"{wood}_log", {"axis": "y"}))
                else:
                    editor.placeBlock((x, y, z), Block(f"{wood}_log", {"axis": "y"}))
            # Arch across the top of the opening
            if abs(dx_gate) <= gate_opening_w:
                editor.placeBlock((x, gate_base_y + gate_opening_h, z), Block(f"{wood}_log", {"axis": "x"}))
                editor.placeBlock((x, gate_base_y + gate_opening_h + 1, z), Block(f"{wood}_log", {"axis": "x"}))
            # Fill foundation down to ground
            for fy in range(ground_y - 5, gate_base_y):
                editor.placeBlock((x, fy, z), Block(f"{wood}_log", {"axis": "y"}))
        else:
            for y in range(base_y, base_y + curr_wall_h):
                editor.placeBlock((x, y, z), get_random_wall_block())
            for fy in range(base_y - 1, ground_y - 15, -1):
                editor.placeBlock((x, fy, z), get_random_wall_block())
            # little crenellations
            if random.random() < 0.5:
                editor.placeBlock((x, base_y + curr_wall_h, z), get_random_wall_block())

    # Flatten / ramp the ground around the gate so it meets the gate base cleanly
    print("flattening ground around gate...")
    for gdx in range(-gate_half_w - 4, gate_half_w + 5):
        for gdz in range(-8, 8):
            gx = gate_cx + gdx
            gz = gate_cz + gdz
            ghx = gx - buildArea.begin.x
            ghz = gz - buildArea.begin.z
            if 0 <= ghx < buildArea.size.x and 0 <= ghz < buildArea.size.z:
                local_g = int(heightmap[ghx][ghz])
                if local_g < gate_base_y:
                    # Fill up terrain to gate level
                    for fy in range(local_g, gate_base_y):
                        editor.placeBlock((gx, fy, gz), Block("stone_bricks"))
                    editor.placeBlock((gx, gate_base_y, gz), Block("cobblestone"))
                elif local_g > gate_base_y + 1:
                    # Cut down terrain to gate level
                    for fy in range(gate_base_y + 1, local_g + 4):
                        editor.placeBlock((gx, fy, gz), Block("air"))
                    editor.placeBlock((gx, gate_base_y, gz), Block("cobblestone"))

    keep_h = 15
    glass_colors = ["red_stained_glass", "blue_stained_glass", "yellow_stained_glass", 
                    "green_stained_glass", "purple_stained_glass", "cyan_stained_glass"]

    print("building keep...")
    for dx in range(-30, 30):
        for dz in range(-25, 35):
            x = cx + dx
            z = cz + dz
            
            if is_inside(dx, dz):
                wall_flag = is_wall(dx, dz)
                
                # solid base
                hx, hz = x - buildArea.begin.x, z - buildArea.begin.z
                local_ground = int(heightmap[hx][hz]) if (0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z) else center_y

                for fy in range(local_ground - 5, keep_base_y):
                    editor.placeBlock((x, fy, z), get_random_wall_block())
                
                # glowstone pattern on floor
                if wall_flag == False and dx % 5 == 0 and dz % 5 == 0:
                    editor.placeBlock((x, keep_base_y, z), Block("glowstone"))
                else:
                    editor.placeBlock((x, keep_base_y, z), Block("cobblestone"))
                
                # pick window colour
                col_index = (abs(dx) * 7 + abs(dz) * 3) % len(glass_colors)
                w_block = Block(glass_colors[col_index])
                
                door_flag = False
                if dz == 30 and -2 <= dx <= 2:
                    door_flag = True
                
                for y in range(keep_base_y + 1, keep_base_y + keep_h):
                    if wall_flag:
                        if door_flag == True and y <= keep_base_y + 4:
                            editor.placeBlock((x, y, z), Block("air"))
                        elif is_window_column(dx, dz) and keep_base_y + 3 <= y <= keep_base_y + keep_h - 3:
                            editor.placeBlock((x, y, z), w_block)
                        else:
                            editor.placeBlock((x, y, z), get_random_wall_block())
                    else:
                        editor.placeBlock((x, y, z), Block("air"))
                        
                # lights on ceiling
                if wall_flag == False and dx % 5 == 0 and dz % 5 == 0:
                    editor.placeBlock((x, keep_base_y + keep_h - 1, z), Block("glowstone"))

    print("adding throne and red carpet...")
    for dz in range(-17, 29):
        editor.placeBlock((cx, keep_base_y, cz + dz), Block("red_wool"))
        editor.placeBlock((cx - 1, keep_base_y, cz + dz), Block("red_wool"))
        editor.placeBlock((cx + 1, keep_base_y, cz + dz), Block("red_wool"))

    throne_z = cz - 18
    
    # pedestal
    for dx in range(-2, 3):
        for dz in range(-1, 2):
            editor.placeBlock((cx + dx, keep_base_y + 1, throne_z + dz), Block("gold_block"))
            
    # stairs to pedestal
    editor.placeBlock((cx, keep_base_y + 1, throne_z + 2), Block("stone_brick_stairs", {"facing": "north"}))
    editor.placeBlock((cx - 1, keep_base_y + 1, throne_z + 2), Block("stone_brick_stairs", {"facing": "north"}))
    editor.placeBlock((cx + 1, keep_base_y + 1, throne_z + 2), Block("stone_brick_stairs", {"facing": "north"}))

    # the golden throne
    ty = keep_base_y + 2
    editor.placeBlock((cx, ty, throne_z), Block("gold_block")) # seat
    
    # backrest
    editor.placeBlock((cx, ty + 1, throne_z), Block("gold_block"))
    editor.placeBlock((cx, ty + 2, throne_z), Block("gold_block"))
    editor.placeBlock((cx, ty + 3, throne_z), Block("gold_block"))
    
    # arms
    editor.placeBlock((cx - 1, ty, throne_z), Block("gold_block"))
    editor.placeBlock((cx + 1, ty, throne_z), Block("gold_block"))
    
    # side pillars
    editor.placeBlock((cx - 2, ty, throne_z), Block("gold_block"))
    editor.placeBlock((cx - 2, ty + 1, throne_z), Block("gold_block"))
    editor.placeBlock((cx + 2, ty, throne_z), Block("gold_block"))
    editor.placeBlock((cx + 2, ty + 1, throne_z), Block("gold_block"))
    
    # lanterns
    editor.placeBlock((cx - 2, ty + 2, throne_z), Block("lantern"))
    editor.placeBlock((cx + 2, ty + 2, throne_z), Block("lantern"))

    # door canopy
    for dx in range(-3, 4):
        for dz in range(31, 33):
            editor.placeBlock((cx + dx, keep_base_y + 5, cz + dz), Block(f"{wood}_slab", {"type": "top"}))
            if abs(dx) == 3:
                for y in range(keep_base_y + 1, keep_base_y + 5):
                    editor.placeBlock((cx + dx, y, cz + dz), Block(f"{wood}_fence"))

    print("building entrance stairs...")

    # Variables for the L-shape stairs
    s_y = keep_base_y
    # 1. Straight run South (5 wide)
    for dz in range(31, 38):
        for dx in range(-2, 3):
            x = cx + dx
            z = cz + dz
            editor.placeBlock((x, s_y, z), Block("stone_brick_stairs", {"facing": "north"}))

            # Fill under the stairs
            hx, hz = x - buildArea.begin.x, z - buildArea.begin.z
            if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:
                g_y = int(heightmap[hx][hz])
                for fy in range(g_y - 2, s_y):
                    editor.placeBlock((x, fy, z), Block("stone_bricks"))
        s_y -= 1  # Go down one step

    for dx in range(-2, 3):
        for dz in range(38, 43):
            x = cx + dx
            z = cz + dz
            editor.placeBlock((x, s_y, z), Block("stone_bricks"))
            hx, hz = x - buildArea.begin.x, z - buildArea.begin.z
            if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:
                g_y = int(heightmap[hx][hz])
                for fy in range(g_y - 2, s_y):
                    editor.placeBlock((x, fy, z), Block("stone_bricks"))

    cur_x = cx - 3  # Start the next run just west of the landing

    # 2. Turn West and descend to ground
    while True:
        # Check ground height at the current X position
        check_hx = cur_x - buildArea.begin.x
        check_hz = (cz + 40) - buildArea.begin.z  # middle of the landing z-range
        if not (0 <= check_hx < buildArea.size.x and 0 <= check_hz < buildArea.size.z): break

        g_y = int(heightmap[check_hx][check_hz])

        # If we reached the ground level or below, build a platform and stop
        if s_y <= g_y:
            for px in range(cur_x - 2, cur_x + 1):
                for pz in range(38, 43):
                    editor.placeBlock((px, s_y, cz + pz), Block("stone_bricks"))
                    # Fill under platform
                    lhx, lhz = px - buildArea.begin.x, (cz + pz) - buildArea.begin.z
                    if 0 <= lhx < buildArea.size.x and 0 <= lhz < buildArea.size.z:
                        lg_y = int(heightmap[lhx][lhz])
                        for fy in range(lg_y - 2, s_y):
                            editor.placeBlock((px, fy, cz + pz), Block("stone_bricks"))
            break

        # Build the 5-wide stair step going West (5 blocks deep in z)
        for dz in range(38, 43):
            z = cz + dz
            editor.placeBlock((cur_x, s_y, z), Block("stone_brick_stairs", {"facing": "east"}))

            # Fill under
            hx, hz = cur_x - buildArea.begin.x, z - buildArea.begin.z
            if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:
                g_y = int(heightmap[hx][hz])
                for fy in range(g_y - 2, s_y):
                    editor.placeBlock((cur_x, fy, z), Block("stone_bricks"))

        cur_x -= 1  # Move West
        s_y -= 1  # Go down

    print("doing roofs...")
    roof_base = keep_base_y + keep_h
    for dx in range(-30, 30):
        for dz in range(-25, 35):
            x = cx + dx
            z = cz + dz
            if is_inside(dx, dz):
                # math for the roof height
                if -25 <= dx <= 25 and -20 <= dz <= 0:
                    ha = min(dz + 20, 0 - dz)
                else:
                    ha = -1
                    
                if -10 <= dx <= 10 and -20 <= dz <= 30:
                    hb = min(dx + 10, 10 - dx)
                else:
                    hb = -1
                    
                target_h = max(ha, hb)
                
                if target_h >= 0:
                    roof_y = roof_base + target_h
                    if is_wall(dx, dz):
                        for fill_y in range(roof_base, roof_y):
                            editor.placeBlock((x, fill_y, z), get_random_wall_block())
                    editor.placeBlock((x, roof_y, z), get_random_roof_block())

    print("building towers...")
    corners = [(-25, -20), (25, -20), (-25, 0), (25, 0), (-10, 30), (10, 30)]
    tower_h = keep_h + 15 
    
    for t in corners:
        tx = cx + t[0]
        tz = cz + t[1]
        
        for dy in range(tower_h):
            y = keep_base_y + dy
            
            # foundation for towers
            if dy == 0:
                hx, hz = tx - buildArea.begin.x, tz - buildArea.begin.z
                local_ground = int(heightmap[hx][hz]) if (0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z) else center_y
                for fy in range(local_ground - 5, keep_base_y):
                    for dx in range(-4, 4):
                        for dz in range(-4, 4):
                            if math.sqrt((dx + 0.5)**2 + (dz + 0.5)**2) <= 4.0:
                                editor.placeBlock((tx + dx, fy, tz + dz), get_random_wall_block())

            # tower walls
            for dx in range(-4, 4):
                for dz in range(-4, 4):
                    if math.sqrt((dx + 0.5)**2 + (dz + 0.5)**2) <= 4.0:
                        editor.placeBlock((tx + dx, y, tz + dz), get_random_wall_block())
                        
        # tower roofs
        t_roof_base = keep_base_y + tower_h
        for dy in range(8):
            rad = max(0, 4 - (dy // 2))
            y = t_roof_base + dy
            for dx in range(-rad - 1, rad + 1):
                for dz in range(-rad - 1, rad + 1):
                    if math.sqrt((dx + 0.5)**2 + (dz + 0.5)**2) <= rad + 0.5:
                        editor.placeBlock((tx + dx, y, tz + dz), get_random_roof_block())

    print("filling in water within the castle grounds - making islands")
    # Use two heightmaps to reliably detect water:
    # MOTION_BLOCKING includes water, OCEAN_FLOOR does not.
    # If MOTION_BLOCKING > OCEAN_FLOOR at a spot, the difference is water.
    hm_surface = worldSlice.heightmaps["MOTION_BLOCKING"]
    hm_floor = worldSlice.heightmaps["OCEAN_FLOOR"]

    # Simple value-noise island generator
    # First pass: collect all water cells
    water_cells = {}  # (dx, dz) -> (x, z, hx, hz, surface_y, floor_y)
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            if dx**2 + dz**2 <= radius**2:
                x = cx + dx
                z = cz + dz
                hx = x - buildArea.begin.x
                hz = z - buildArea.begin.z
                if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:
                    surface_y = int(hm_surface[hx][hz])
                    floor_y = int(hm_floor[hx][hz])
                    if surface_y > floor_y:
                        water_cells[(dx, dz)] = (x, z, hx, hz, surface_y, floor_y)

    # Generate island seeds near water areas
    island_centers = []
    island_seed = random.randint(0, 999999)
    rng_islands = random.Random(island_seed)
    for (dx, dz) in water_cells:
        # Sparse island seeds
        if rng_islands.random() < 0.008:
            island_r = rng_islands.uniform(3, 8)
            island_centers.append((dx, dz, island_r))

    # Also seed islands along the shoreline (where water meets land) for natural bridging
    for (dx, dz) in water_cells:
        for ndx, ndz in [(dx+1,dz),(dx-1,dz),(dx,dz+1),(dx,dz-1)]:
            if (ndx, ndz) not in water_cells and ndx**2 + ndz**2 <= radius**2:
                if rng_islands.random() < 0.06:
                    island_r = rng_islands.uniform(2, 5)
                    island_centers.append((dx, dz, island_r))
                break

    # For each water cell, check if it falls inside any island
    water_filled = 0
    for (dx, dz), (x, z, hx, hz, surface_y, floor_y) in water_cells.items():
        water_top = surface_y - 1
        water_bottom = floor_y

        # Check distance to closest island center
        fill = False
        for (ic_dx, ic_dz, ic_r) in island_centers:
            dist = math.sqrt((dx - ic_dx)**2 + (dz - ic_dz)**2)
            if dist <= ic_r:
                fill = True
                break

        if fill:
            # Fill with dirt, top with a natural surface block
            for fy in range(water_bottom, water_top + 1):
                editor.placeBlock((x, fy, z), Block("dirt"))

            top_block = random.choice(ground_textures)
            editor.placeBlock((x, water_top, z), Block(top_block))

            # Add occasional grass/vegetation on top
            if random.random() < 0.15:
                editor.placeBlock((x, water_top + 1, z), Block("short_grass"))
            elif random.random() < 0.04:
                editor.placeBlock((x, water_top + 1, z), Block("poppy"))

            heightmap[hx][hz] = water_top + 1
            water_filled += 1

    print(f"filled {water_filled} water columns")

    print("spawning huts and deposits...")
    huts_list = []
    options = ["blacksmith", "merchant", "hay", "coal_deposit", "iron_deposit", "copper_deposit"]
    
    for dx in range(-45, 46):
        for dz in range(-45, 46):
            dist_center = math.sqrt(dx**2 + dz**2)
            dist_gate = math.sqrt(dx**2 + (dz - radius)**2)
            
            x = cx + dx
            z = cz + dz
            hx = x - buildArea.begin.x
            hz = z - buildArea.begin.z
            
            ground_y = heightmap[hx][hz]
            # check if empty space
            if dist_center < 45 and not is_inside(dx, dz) and not is_stairs(dx, dz):
                if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:

                    # random texture blocks
                    if random.random() < 0.20:
                        t_block = random.choice(ground_textures)
                        editor.placeBlock((x, ground_y - 1, z), Block(t_block))

                # maybe spawn a hut
                if dist_gate > 12 and random.random() < 0.02:
                    too_close = False
                    for prev_hut in huts_list:
                        hut_dist = math.sqrt((dx - prev_hut[0])**2 + (dz - prev_hut[1])**2)
                        if hut_dist < 7:
                            too_close = True
                            break
                    
                    if too_close == False:
                        huts_list.append((dx, dz))
                        h_type = random.choice(options)
                        build_hut(x, ground_y, z, h_type, wood, editor)

    print("done! generated", len(huts_list), "huts")

if __name__ == "__main__":
    build_castle()