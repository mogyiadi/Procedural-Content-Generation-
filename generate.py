import sys
import math
import random
from gdpc import Editor, Block

editor = Editor(buffering=True)

# global stair direction: randomly set to "west" or "east" in build_castle()
stair_direction = "west"

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
        if b is not None:
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
        pass

    return wood_type, ground

# generates a random color and geometric pattern for the floor
def get_mosaic_block(dx, dz, style, palette, scale1, scale2):
    # use absolute values to ensure the pattern is perfectly symmetrical
    # across all 4 quadrants of the keep
    ax, az = abs(dx), abs(dz)

    if style == 0:
        # fractal / sierpinski triangle pattern (bitwise xor)
        idx = (ax ^ az)
    elif style == 1:
        # diagonal diamond / chevron patterns
        idx = (ax // scale1) + (az // scale2)
    elif style == 2:
        # concentric circular rings
        idx = int(math.hypot(ax, az) / scale1)
    else:
        # plaid / checkerboard patterns
        idx = (ax // scale1) * (az // scale2)

    return Block(palette[idx % len(palette)])

# sample nearby blocks and return the most common solid ground block
def sample_foundation_block(worldSlice, local_x, y, local_z):
    from collections import Counter

    invalid_keywords = [
        "leaves", "log", "vine", "bamboo", "mushroom", "flower", "bush",
        "sapling", "grass", "fern", "air", "water", "lava", "snow",
        "ice", "fire", "torch", "lantern", "carpet", "azalea",
        "hanging_roots", "propagule", "cocoa", "bee_nest", "moss_carpet",
        "tall_grass", "short_grass", "dead_bush", "kelp", "seagrass",
        "lily_pad", "sugar_cane", "cactus", "sweet_berry", "cave_vines",
        "glow_lichen", "mangrove_roots", "wood"
    ]

    sample_offsets = []
    rng = random.Random()
    for _ in range(10):
        sdx = rng.randint(-5, 5)
        sdz = rng.randint(-5, 5)
        sample_offsets.append((sdx, sdz))

    block_counts = Counter()
    for (sdx, sdz) in sample_offsets:
        sx = local_x + sdx
        sz = local_z + sdz
        try:
            blk = worldSlice.getBlockGlobal((sx, y - 1, sz)).id
            is_invalid = False
            for kw in invalid_keywords:
                if kw in blk:
                    is_invalid = True
                    break
            if not is_invalid and blk != "minecraft:air":
                clean_id = blk.replace("minecraft:", "")
                block_counts[clean_id] += 1
        except:
            pass

    if block_counts:
        return block_counts.most_common(1)[0][0]
    else:
        return "cobblestone"

# find solid ground y at a given x,z by scanning downward
def find_solid_ground_y(worldSlice, x, y, z):
    non_solid_keywords = [
        "air", "leaves", "log", "vine", "bamboo", "water", "lava",
        "grass", "fern", "flower", "mushroom", "bush", "sapling",
        "tall_grass", "short_grass", "snow_layer", "fire", "torch",
        "kelp", "seagrass", "lily_pad", "sugar_cane", "cactus",
        "hanging_roots", "cave_vines", "glow_lichen", "wood",
        "moss_carpet", "dead_bush", "sweet_berry"
    ]
    scan_y = y
    while scan_y > -64:
        try:
            blk = worldSlice.getBlockGlobal((x, scan_y, z)).id
            is_non_solid = False
            for kw in non_solid_keywords:
                if kw in blk:
                    is_non_solid = True
                    break
            if not is_non_solid:
                return scan_y
        except:
            pass
        scan_y -= 1
    return y

# builds small hut or deposit
def build_hut(local_x, y, local_z, h_type, wood, editor, worldSlice=None):
    # clear space first
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            for dy in range(1, 5):
                editor.placeBlock((local_x + dx, y + dy, local_z + dz), Block("air"))

    # sample nearby blocks to determine foundation material
    # and place a foundation layer below the hut floor
    if h_type not in ["coal_deposit", "iron_deposit", "copper_deposit", "hay"]:
        if worldSlice is not None:
            foundation_block = sample_foundation_block(worldSlice, local_x, y, local_z)
        else:
            foundation_block = "cobblestone"

        for dx in range(-2, 3):
            for dz in range(-2, 3):
                editor.placeBlock((local_x + dx, y - 1, local_z + dz), Block(foundation_block))

    if h_type == "blacksmith":
        # cobblestone floor and slab roof
        for dx in range(-2, 3):
            for dz in range(-2, 3):
                editor.placeBlock((local_x + dx, y, local_z + dz), Block("cobblestone"))
                editor.placeBlock((local_x + dx, y + 4, local_z + dz), Block("cobblestone_slab"))

        # log pillars in each corner
        for dx, dz in [(-2,-2), (2,-2), (-2,2), (2,2)]:
            for dy in range(1, 4):
                editor.placeBlock((local_x + dx, y + dy, local_z + dz), Block(f"{wood}_log", {"axis": "y"}))

        # blacksmith equipment
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
        # find solid ground so hay doesn't float
        if worldSlice is not None:
            hay_ground = find_solid_ground_y(worldSlice, local_x, y, local_z)
        else:
            hay_ground = y
        editor.placeBlock((local_x, hay_ground + 1, local_z), Block("hay_block", {"axis": "y"}))
        editor.placeBlock((local_x + 1, hay_ground + 1, local_z), Block("hay_block", {"axis": "x"}))
        editor.placeBlock((local_x, hay_ground + 2, local_z), Block("hay_block", {"axis": "y"}))
        editor.placeBlock((local_x - 1, hay_ground + 1, local_z), Block("composter"))

    elif h_type in ["coal_deposit", "iron_deposit", "copper_deposit"]:
        if h_type == "coal_deposit":
            ore = "coal_block"
        elif h_type == "iron_deposit":
            ore = "raw_iron_block"
        else:
            ore = "raw_copper_block"

        # find actual solid ground for each ore block so they don't float
        for dx in range(-1, 2):
            for dz in range(-1, 2):
                if random.random() < 0.6:
                    ox = local_x + dx
                    oz = local_z + dz
                    if worldSlice is not None:
                        ground = find_solid_ground_y(worldSlice, ox, y, oz)
                    else:
                        ground = y
                    editor.placeBlock((ox, ground, oz), Block(ore))
                    editor.placeBlock((ox, ground + 1, oz), Block(ore))
        if worldSlice is not None:
            center_ground = find_solid_ground_y(worldSlice, local_x, y, local_z)
        else:
            center_ground = y
        editor.placeBlock((local_x, center_ground, local_z), Block(ore))
        editor.placeBlock((local_x, center_ground + 1, local_z), Block(ore))
        editor.placeBlock((local_x, center_ground + 2, local_z), Block(ore))

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
    # straight run going south from the keep entrance
    if -3 <= dx <= 3 and 31 <= dz <= 37:
        return True
    # landing platform and the descent (west or east depending on stair_direction)
    if stair_direction == "west":
        if -22 <= dx <= 3 and 38 <= dz <= 43:
            return True
        # potential north turn
        if -22 <= dx <= -14 and 0 <= dz <= 43:
            return True
    else:
        if -3 <= dx <= 22 and 38 <= dz <= 43:
            return True
        # potential north turn
        if 14 <= dx <= 22 and 0 <= dz <= 43:
            return True
    return False

# main function to build castle
def build_castle():
    global stair_direction
    stair_direction = random.choice(["west", "east"])
    print("stair direction:", stair_direction)

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

    # walk around a circle to get all the perimeter positions for the outer wall
    perimeter_points = []
    for angle in range(360):
        rad = math.radians(angle)
        x_pos = int(cx + radius * math.cos(rad))
        z_pos = int(cz + radius * math.sin(rad))
        if (x_pos, z_pos) not in perimeter_points:
            perimeter_points.append((x_pos, z_pos))

    # sort by angle so the wall draws smoothly around the circle
    perimeter_points.sort(key=lambda p: math.atan2(p[1] - cz, p[0] - cx))

    prev_y = None
    wall_bases = []
    # set version for quick membership checks
    perimeter_set = set(perimeter_points)

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

        # make walls taller if next to a cliff
        max_surrounding_y = ground_y
        angle = math.atan2(z - cz, x - cx)
        hm_ground = worldSlice.heightmaps["OCEAN_FLOOR"]
        for out_dist in range(1, 9):
            ox = int(x + out_dist * math.cos(angle))
            oz = int(z + out_dist * math.sin(angle))
            ohx = ox - buildArea.begin.x
            ohz = oz - buildArea.begin.z
            # skip if this point is on the wall perimeter itself
            if (ox, oz) in perimeter_set:
                continue
            if 0 <= ohx < buildArea.size.x and 0 <= ohz < buildArea.size.z:
                out_y = int(hm_ground[ohx][ohz])
                if out_y > max_surrounding_y:
                    max_surrounding_y = out_y

        # ensure the wall is at least 10 blocks taller than the highest nearby point
        # Cap the extra height so walls never get absurdly tall
        local_wall_h = max(wall_height, (max_surrounding_y - base_y) + 10)
        local_wall_h = min(local_wall_h, wall_height + 50)

        # Smooth out sudden jumps in base_y so the wall doesn't teleport
        # up or down, but still gradually returns to the true ground level.
        # Allow the base to change by at most 3 blocks per column.
        max_step = 3
        if prev_y is not None:
            if base_y < prev_y - max_step:
                base_y = prev_y - max_step
            elif base_y > prev_y + max_step:
                base_y = prev_y + max_step

        wall_bases.append((x, base_y, z, ground_y, local_wall_h))
        prev_y = base_y

    print("building walls...")
    for w in wall_bases:
        x = w[0]
        base_y = w[1]
        z = w[2]
        ground_y = w[3]
        curr_wall_h = w[4]

        for y in range(base_y, base_y + curr_wall_h):
            editor.placeBlock((x, y, z), get_random_wall_block())
        for fy in range(base_y - 1, ground_y - 15, -1):
            editor.placeBlock((x, fy, z), get_random_wall_block())
        # little crenellations
        if random.random() < 0.5:
            editor.placeBlock((x, base_y + curr_wall_h, z), get_random_wall_block())

    print("building outer wall gate...")
    # the gate sits on the south side of the circular wall, lined up with the keep entrance
    gate_z_wall = cz + radius
    # find the lowest wall base near the gate opening
    gate_base_y = None
    gate_wall_h = wall_height
    for w in wall_bases:
        if abs(w[0] - cx) <= 3 and abs(w[2] - gate_z_wall) <= 2:
            if gate_base_y is None or w[1] < gate_base_y:
                gate_base_y = w[1]
                gate_wall_h = w[4]

    # fallback if no matching wall column was found
    if gate_base_y is None:
        gate_base_y = center_y

    # clear a 5-wide, 5-tall opening in the wall for the gate
    for gdx in range(-2, 3):
        gx = cx + gdx
        for gz_off in range(-1, 2):
            gz = gate_z_wall + gz_off
            # only clear blocks that are actually part of the perimeter
            if (gx, gz) in perimeter_set:
                for gy in range(gate_base_y, gate_base_y + 5):
                    editor.placeBlock((gx, gy, gz), Block("air"))

    # two tall log pillars on either side of the gate
    for side_dx in [-3, 3]:
        gx = cx + side_dx
        for gz_off in range(-1, 2):
            gz = gate_z_wall + gz_off
            for gy in range(gate_base_y, gate_base_y + 7):
                editor.placeBlock((gx, gy, gz), Block(f"{wood}_log", {"axis": "y"}))
            # cap the pillar with a stripped log
            editor.placeBlock((gx, gate_base_y + 7, gz), Block(f"stripped_{wood}_log", {"axis": "y"}))

    # crossbeam across the top
    for gdx in range(-3, 4):
        gx = cx + gdx
        for gz_off in range(-1, 2):
            gz = gate_z_wall + gz_off
            editor.placeBlock((gx, gate_base_y + 5, gz), Block(f"{wood}_planks"))
            editor.placeBlock((gx, gate_base_y + 6, gz), Block(f"{wood}_slab", {"type": "bottom"}))

    # wooden arch detail on front face
    for gdx in range(-2, 3):
        gx = cx + gdx
        gz = gate_z_wall + 1
        editor.placeBlock((gx, gate_base_y + 5, gz), Block(f"stripped_{wood}_log", {"axis": "x"}))

    # trapdoors along the inner sides of the gate for decoration
    for side_dx in [-2, 2]:
        gx = cx + side_dx
        facing = "west" if side_dx == 2 else "east"
        for gy in range(gate_base_y, gate_base_y + 5):
            editor.placeBlock((gx, gy, gate_z_wall - 1), Block(f"{wood}_trapdoor", {"facing": facing, "open": "true", "half": "bottom"}))
            editor.placeBlock((gx, gy, gate_z_wall + 1), Block(f"{wood}_trapdoor", {"facing": facing, "open": "true", "half": "bottom"}))

    # lanterns hanging from the crossbeam
    editor.placeBlock((cx - 1, gate_base_y + 4, gate_z_wall + 1), Block("lantern", {"hanging": "true"}))
    editor.placeBlock((cx + 1, gate_base_y + 4, gate_z_wall + 1), Block("lantern", {"hanging": "true"}))

    # banner decorations on the pillars
    for side_dx in [-3, 3]:
        gx = cx + side_dx
        editor.placeBlock((gx, gate_base_y + 6, gate_z_wall + 2), Block("red_banner", {"rotation": "8"}))

    # clear the area outside the gate so there's a walkable approach
    print("clearing area outside the gate...")
    for gdx in range(-4, 5):
        # 8 blocks outward from the wall
        for gz_off in range(2, 10):
            gx = cx + gdx
            gz = gate_z_wall + gz_off
            ghx = gx - buildArea.begin.x
            ghz = gz - buildArea.begin.z
            if 0 <= ghx < buildArea.size.x and 0 <= ghz < buildArea.size.z:
                ground_at = int(heightmap[ghx][ghz])
                # remove blocks above the ground so you can actually walk through
                for gy in range(ground_at, gate_base_y + 7):
                    editor.placeBlock((gx, gy, gz), Block("air"))
                editor.placeBlock((gx, ground_at - 1, gz), Block("cobblestone"))

    keep_h = 15
    glass_colors = ["red_stained_glass", "blue_stained_glass", "yellow_stained_glass",
                    "green_stained_glass", "purple_stained_glass", "cyan_stained_glass"]

    print("building keep...")
    # --- setup random mosaic variables for this generation ---
    all_terracotta = [
        "white", "light_gray", "gray", "black", "brown", "red", "orange",
        "yellow", "lime", "green", "cyan", "light_blue", "blue", "purple", "magenta", "pink"
    ]
    # pick a random palette of 3 to 5 colors for this specific castle
    mosaic_palette = [c + "_terracotta" for c in random.sample(all_terracotta, random.randint(3, 5))]
    # pick a random geometric style and scaling factors
    mosaic_style = random.randint(0, 3)
    mosaic_s1 = random.randint(2, 5)
    mosaic_s2 = random.randint(2, 5)
    # ---------------------------------------------------------

    for dx in range(-30, 30):
        for dz in range(-25, 35):
            x = cx + dx
            z = cz + dz

            if is_inside(dx, dz):
                wall_flag = is_wall(dx, dz)

                # solid base
                hx, hz = x - buildArea.begin.x, z - buildArea.begin.z
                local_ground = int(heightmap[hx][hz]) if (0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z) else center_y

                for fy in range(max(-64, local_ground - 5), keep_base_y):
                    editor.placeBlock((x, fy, z), get_random_wall_block())

                # glowstone pattern on floor
                if wall_flag == False and dx % 5 == 0 and dz % 5 == 0:
                    editor.placeBlock((x, keep_base_y, z), Block("glowstone"))
                elif wall_flag == False:
                    # place the procedural mosaic on the interior floor
                    m_block = get_mosaic_block(dx, dz, mosaic_style, mosaic_palette, mosaic_s1, mosaic_s2)
                    editor.placeBlock((x, keep_base_y, z), m_block)
                else:
                    # put cobblestone under the actual walls
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

    for dx in range(-3, 4):
        for dz in range(-2, 3):
            editor.placeBlock((cx + dx, keep_base_y + 1, throne_z + dz), Block("polished_blackstone"))
    for dx in range(-3, 4):
        editor.placeBlock((cx + dx, keep_base_y + 1, throne_z + 3), Block("polished_blackstone_stairs", {"facing": "north"}))

    for dx in range(-2, 3):
        for dz in range(-1, 2):
            editor.placeBlock((cx + dx, keep_base_y + 2, throne_z + dz), Block("gold_block"))
    for dx in range(-2, 3):
        editor.placeBlock((cx + dx, keep_base_y + 2, throne_z + 2), Block("polished_blackstone_stairs", {"facing": "north"}))

    for dx in range(-1, 2):
        editor.placeBlock((cx + dx, keep_base_y + 3, throne_z), Block("gold_block"))
        editor.placeBlock((cx + dx, keep_base_y + 3, throne_z - 1), Block("gold_block"))
    for dx in range(-1, 2):
        editor.placeBlock((cx + dx, keep_base_y + 3, throne_z + 1), Block("gold_block"))

    ty = keep_base_y + 4

    # quartz stair seat
    editor.placeBlock((cx, ty, throne_z), Block("quartz_stairs", {"facing": "south", "half": "bottom"}))

    # armrests
    editor.placeBlock((cx - 1, ty, throne_z), Block("end_stone_brick_wall"))
    editor.placeBlock((cx + 1, ty, throne_z), Block("end_stone_brick_wall"))

    # backrest
    editor.placeBlock((cx, ty, throne_z - 1), Block("gold_block"))
    editor.placeBlock((cx, ty + 1, throne_z - 1), Block("gold_block"))
    editor.placeBlock((cx, ty + 2, throne_z - 1), Block("gold_block"))
    editor.placeBlock((cx, ty + 3, throne_z - 1), Block("gold_block"))

    # extra decoration
    editor.placeBlock((cx, ty + 4, throne_z - 1), Block("lightning_rod"))
    editor.placeBlock((cx - 1, ty + 3, throne_z - 1), Block("gold_block"))
    editor.placeBlock((cx + 1, ty + 3, throne_z - 1), Block("gold_block"))
    editor.placeBlock((cx - 1, ty + 4, throne_z - 1), Block("end_rod", {"facing": "up"}))
    editor.placeBlock((cx + 1, ty + 4, throne_z - 1), Block("end_rod", {"facing": "up"}))

    # side pillars with chains and lanterns
    for side in [-1, 1]:
        px = cx + side * 3
        # pillar base
        editor.placeBlock((px, keep_base_y + 1, throne_z), Block("polished_blackstone"))
        for py in range(keep_base_y + 2, ty + 5):
            editor.placeBlock((px, py, throne_z), Block("quartz_pillar", {"axis": "y"}))
        # pillar cap
        editor.placeBlock((px, ty + 5, throne_z), Block("gold_block"))
        editor.placeBlock((px, ty + 6, throne_z), Block("soul_lantern"))

        # chain + lantern hanging inward
        editor.placeBlock((cx + side * 2, ty + 4, throne_z), Block("iron_bars"))
        editor.placeBlock((cx + side * 2, ty + 3, throne_z), Block("lantern", {"hanging": "true"}))

    # red banners behind the throne
    for side in [-1, 0, 1]:
        bx = cx + side * 2
        editor.placeBlock((bx, ty + 2, throne_z - 2), Block("red_banner", {"rotation": "8"}))

    for dx in range(-3, 4):
        editor.placeBlock((cx + dx, keep_base_y + 1, throne_z - 3), Block("chiseled_polished_blackstone"))
    for dz in range(-3, 3):
        editor.placeBlock((cx - 4, keep_base_y + 1, throne_z + dz), Block("chiseled_polished_blackstone"))
        editor.placeBlock((cx + 4, keep_base_y + 1, throne_z + dz), Block("chiseled_polished_blackstone"))

    # glowstone under the throne
    editor.placeBlock((cx - 1, keep_base_y + 2, throne_z - 1), Block("glowstone"))
    editor.placeBlock((cx + 1, keep_base_y + 2, throne_z - 1), Block("glowstone"))

    # summon technoblade
    editor.runCommandGlobal(
        f'summon minecraft:pig {cx} {ty + 1} {throne_z} '
        f'{{CustomName:\'"Technoblade"\',CustomNameVisible:1b,Invulnerable:1b,Silent:1b,NoAI:1b,NoGravity:1b,PersistenceRequired:1b}}'
    )

    # door canopy
    for dx in range(-3, 4):
        for dz in range(31, 33):
            editor.placeBlock((cx + dx, keep_base_y + 5, cz + dz), Block(f"{wood}_slab", {"type": "top"}))
            if abs(dx) == 3:
                for y in range(keep_base_y + 1, keep_base_y + 5):
                    editor.placeBlock((cx + dx, y, cz + dz), Block(f"{wood}_fence"))

    print("adding interior decor...")

    # dining tables and benches in the left and right wings of the main hall
    for wing_center_dx in [-16, 16]:
        # two columns of tables per wing
        for table_dx_off in [-3, 3]:
            table_dx = wing_center_dx + table_dx_off
            # skip if too close to the walls
            if abs(table_dx) > 23 or abs(table_dx) < 12:
                continue
            for table_dz in range(-16, -3, 2):
                tx = cx + table_dx
                tz = cz + table_dz
                # table
                editor.placeBlock((tx, keep_base_y + 1, tz), Block(f"{wood}_fence"))
                editor.placeBlock((tx, keep_base_y + 2, tz), Block(f"{wood}_pressure_plate"))
                # candle above every table
                editor.placeBlock((tx, keep_base_y + 3, tz), Block("candle", {"candles": "3", "lit": "true"}))
                # benches
                editor.placeBlock((tx - 1, keep_base_y + 1, tz), Block(f"{wood}_stairs", {"facing": "east"}))
                editor.placeBlock((tx + 1, keep_base_y + 1, tz), Block(f"{wood}_stairs", {"facing": "west"}))

    # bookshelves lining the walls
    for shelf_dz in range(5, 25, 3):
        for shelf_dx in [-9, 9]:
            sx = cx + shelf_dx
            sz = cz + shelf_dz
            editor.placeBlock((sx, keep_base_y + 1, sz), Block("bookshelf"))
            editor.placeBlock((sx, keep_base_y + 2, sz), Block("bookshelf"))
            if random.random() < 0.3:
                editor.placeBlock((sx, keep_base_y + 3, sz), Block("lantern"))

    # flower pots along corridor
    flower_types = ["potted_poppy", "potted_blue_orchid", "potted_allium",
                    "potted_azure_bluet", "potted_red_tulip", "potted_cornflower"]
    for pot_dz in range(3, 28, 4):
        for pot_dx in [-5, 5]:
            px = cx + pot_dx
            pz = cz + pot_dz
            editor.placeBlock((px, keep_base_y + 1, pz), Block("polished_andesite"))
            editor.placeBlock((px, keep_base_y + 2, pz), Block(random.choice(flower_types)))

    # wall torches
    for torch_dx in range(-22, 23, 4):
        editor.placeBlock((cx + torch_dx, keep_base_y + 3, cz - 19), Block("wall_torch", {"facing": "south"}))
    # side walls
    for torch_dz in range(-17, -1, 4):
        editor.placeBlock((cx - 24, keep_base_y + 3, cz + torch_dz), Block("wall_torch", {"facing": "east"}))
        editor.placeBlock((cx + 24, keep_base_y + 3, cz + torch_dz), Block("wall_torch", {"facing": "west"}))
    # narrow wing walls
    for torch_dz in range(3, 28, 4):
        editor.placeBlock((cx - 9, keep_base_y + 3, cz + torch_dz), Block("wall_torch", {"facing": "east"}))
        editor.placeBlock((cx + 9, keep_base_y + 3, cz + torch_dz), Block("wall_torch", {"facing": "west"}))

    print("building entrance stairs...")

    # keep track of placed stairs, later used for clearing the vegetation from above them
    placed_stair_positions = {}
    s_y = keep_base_y
    # straight run heading south from the keep door
    for dz in range(31, 38):
        for dx in range(-2, 3):
            x = cx + dx
            z = cz + dz
            placed_stair_positions[(x, z)] = s_y
            editor.placeBlock((x, s_y, z), Block("stone_brick_stairs", {"facing": "north"}))

            # fill under the stairs
            hx, hz = x - buildArea.begin.x, z - buildArea.begin.z
            if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:
                g_y = int(heightmap[hx][hz])
                for fy in range(g_y - 2, s_y):
                    editor.placeBlock((x, fy, z), Block("stone_bricks"))
        s_y -= 1

    # flat landing platform where the staircase turns
    for dx in range(-2, 3):
        for dz in range(38, 43):
            x = cx + dx
            z = cz + dz
            placed_stair_positions[(x, z)] = s_y
            editor.placeBlock((x, s_y, z), Block("stone_bricks"))
            hx, hz = x - buildArea.begin.x, z - buildArea.begin.z
            if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:
                g_y = int(heightmap[hx][hz])
                for fy in range(g_y - 2, s_y):
                    editor.placeBlock((x, fy, z), Block("stone_bricks"))

    # start the descent (west or east depending on stair_direction)
    if stair_direction == "west":
        cur_x = cx - 3
        x_step = -1
        stair_facing = "east"
    else:
        cur_x = cx + 3
        x_step = 1
        stair_facing = "west"

    # keep going in the chosen direction, placing steps until ground level
    while True:
        # check ground height at the current x position
        check_hx = cur_x - buildArea.begin.x
        check_hz = (cz + 40) - buildArea.begin.z
        if not (0 <= check_hx < buildArea.size.x and 0 <= check_hz < buildArea.size.z):
            break

        g_y = int(heightmap[check_hx][check_hz])
        
        # check if we need to turn north to avoid the outer wall
        should_turn_north = False
        stair_dz_outer = 43
        wall_x_at_stair = math.sqrt(max(0, radius**2 - stair_dz_outer**2))

        # turning platform is 4 blocks wide, leaving 3 blocks as margin
        turn_threshold = wall_x_at_stair - 4 - 3
        if stair_direction == "west" and (cx - cur_x) >= turn_threshold:
            should_turn_north = True
        elif stair_direction == "east" and (cur_x - cx) >= turn_threshold:
            should_turn_north = True

        if should_turn_north:
            print("Stairs turning north to avoid wall...")
            # building a landing platform for the turn
            if stair_direction == "west":
                plat_x_range = range(cur_x - 4, cur_x + 1)
            else:
                plat_x_range = range(cur_x, cur_x + 5)

            for px in plat_x_range:
                for pz in range(38, 43):
                    placed_stair_positions[(px, cz + pz)] = s_y
                    editor.placeBlock((px, s_y, cz + pz), Block("stone_bricks"))
                    # fill under
                    lhx, lhz = px - buildArea.begin.x, (cz + pz) - buildArea.begin.z
                    if 0 <= lhx < buildArea.size.x and 0 <= lhz < buildArea.size.z:
                        lg_y = int(heightmap[lhx][lhz])
                        for fy in range(lg_y - 2, s_y):
                            editor.placeBlock((px, fy, cz + pz), Block("stone_bricks"))
            
            # descend north from this platform
            cur_z = cz + 37
            
            north_stair_x_range = plat_x_range

            while True:
                # check ground at the center of the new stair segment
                check_hx = (cur_x) - buildArea.begin.x
                check_hz = (cur_z) - buildArea.begin.z
                if not (0 <= check_hx < buildArea.size.x and 0 <= check_hz < buildArea.size.z):
                    break
                g_y_north = int(heightmap[check_hx][check_hz])
                
                if s_y <= g_y_north:
                    # final landing for north stairs
                    for px in north_stair_x_range:
                        for pz_off in range(3):
                            pz = cur_z + pz_off
                            placed_stair_positions[(px, pz)] = s_y
                            editor.placeBlock((px, s_y, pz), Block("stone_bricks"))
                            # fill under
                            lhx, lhz = px - buildArea.begin.x, pz - buildArea.begin.z
                            if 0 <= lhx < buildArea.size.x and 0 <= lhz < buildArea.size.z:
                                lg_y = int(heightmap[lhx][lhz])
                                for fy in range(lg_y - 2, s_y):
                                    editor.placeBlock((px, fy, pz), Block("stone_bricks"))
                    break
                
                # place stairs
                for px in north_stair_x_range:
                    placed_stair_positions[(px, cur_z)] = s_y
                    editor.placeBlock((px, s_y, cur_z), Block("stone_brick_stairs", {"facing": "south"}))
                    # fill under
                    lhx, lhz = px - buildArea.begin.x, cur_z - buildArea.begin.z
                    if 0 <= lhx < buildArea.size.x and 0 <= lhz < buildArea.size.z:
                        lg_y = int(heightmap[lhx][lhz])
                        for fy in range(lg_y - 2, s_y):
                            editor.placeBlock((px, fy, cur_z), Block("stone_bricks"))
                            
                cur_z -= 1
                s_y -= 1
            
            break

        # final landing platform if the stairs don't turn
        if s_y <= g_y:
            if stair_direction == "west":
                plat_range = range(cur_x - 2, cur_x + 1)
            else:
                plat_range = range(cur_x, cur_x + 3)
            for px in plat_range:
                for pz in range(38, 43):
                    placed_stair_positions[(px, cz + pz)] = s_y
                    editor.placeBlock((px, s_y, cz + pz), Block("stone_bricks"))
                    # fill under platform
                    lhx, lhz = px - buildArea.begin.x, (cz + pz) - buildArea.begin.z
                    if 0 <= lhx < buildArea.size.x and 0 <= lhz < buildArea.size.z:
                        lg_y = int(heightmap[lhx][lhz])
                        for fy in range(lg_y - 2, s_y):
                            editor.placeBlock((px, fy, cz + pz), Block("stone_bricks"))
            break

        # stairs going in the chosen direction
        for dz in range(38, 43):
            z = cz + dz
            placed_stair_positions[(cur_x, z)] = s_y
            editor.placeBlock((cur_x, s_y, z), Block("stone_brick_stairs", {"facing": stair_facing}))

            # fill under
            hx, hz = cur_x - buildArea.begin.x, z - buildArea.begin.z
            if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:
                g_y_fill = int(heightmap[hx][hz])
                for fy in range(g_y_fill - 2, s_y):
                    editor.placeBlock((cur_x, fy, z), Block("stone_bricks"))

        cur_x += x_step
        s_y -= 1

    # clear vegetation directly above the stairs
    print("clearing vegetation above stairs...")
    for (sx, sz), stair_y in placed_stair_positions.items():
        shx = sx - buildArea.begin.x
        shz = sz - buildArea.begin.z
        if 0 <= shx < buildArea.size.x and 0 <= shz < buildArea.size.z:
            for sy in range(stair_y + 1, keep_base_y + 25):
                try:
                    blk_id = worldSlice.getBlockGlobal((sx, sy, sz)).id
                    if any(s in blk_id for s in ["log", "wood", "leaves", "vine", "bamboo", "cocoa",
                                                   "mushroom", "bee_nest", "moss_carpet",
                                                   "hanging_roots", "azalea", "mangrove_roots",
                                                   "propagule", "bush", "tall_grass", "short_grass",
                                                   "fern", "dead_bush"]):
                        editor.placeBlock((sx, sy, sz), Block("air"))
                except:
                    pass

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

    # generate a random height for all towers in this specific generation run
    tower_h = keep_h + random.randint(10, 25)
    print(f"tower height: {tower_h} blocks (keep_h={keep_h} + random={tower_h - keep_h})")

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
    # compare two heightmaps to detect water columns:
    # where motion_blocking is higher than ocean_floor, there's water
    hm_surface = worldSlice.heightmaps["MOTION_BLOCKING"]
    hm_floor = worldSlice.heightmaps["OCEAN_FLOOR"]

    # collect all water cells inside the castle walls
    water_cells = {}
    for dx in range(-radius, radius + 1):
        for dz in range(-radius, radius + 1):
            if dx**2 + dz**2 <= radius**2 and not is_stairs(dx, dz):
                x = cx + dx
                z = cz + dz
                hx = x - buildArea.begin.x
                hz = z - buildArea.begin.z
                if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:
                    surface_y = int(hm_surface[hx][hz])
                    floor_y = int(hm_floor[hx][hz])
                    if surface_y > floor_y:
                        water_cells[(dx, dz)] = (x, z, hx, hz, surface_y, floor_y)

    # generate island seeds near water areas
    island_centers = []
    island_seed = random.randint(0, 999999)
    rng_islands = random.Random(island_seed)
    for (dx, dz) in water_cells:
        if rng_islands.random() < 0.008:
            island_r = rng_islands.uniform(3, 8)
            island_centers.append((dx, dz, island_r))

    # extra island seeds along the shoreline so land bridges form naturally
    for (dx, dz) in water_cells:
        for ndx, ndz in [(dx+1,dz),(dx-1,dz),(dx,dz+1),(dx,dz-1)]:
            if (ndx, ndz) not in water_cells and ndx**2 + ndz**2 <= radius**2:
                if rng_islands.random() < 0.06:
                    island_r = rng_islands.uniform(2, 5)
                    island_centers.append((dx, dz, island_r))
                break

    # fill in water cells that fall within an island radius
    water_filled = 0
    for (dx, dz), (x, z, hx, hz, surface_y, floor_y) in water_cells.items():
        water_top = surface_y - 1
        water_bottom = floor_y

        # check distance to closest island center
        fill = False
        for (ic_dx, ic_dz, ic_r) in island_centers:
            dist = math.sqrt((dx - ic_dx)**2 + (dz - ic_dz)**2)
            if dist <= ic_r:
                fill = True
                break

        if fill:
            # fill with dirt, top with a natural surface block
            for fy in range(water_bottom, water_top + 1):
                editor.placeBlock((x, fy, z), Block("dirt"))

            top_block = random.choice(ground_textures)
            editor.placeBlock((x, water_top, z), Block(top_block))

            # occasionally place some plants
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

            x = cx + dx
            z = cz + dz
            hx = x - buildArea.begin.x
            hz = z - buildArea.begin.z

            ground_y = int(heightmap[hx][hz])
            # check if empty space
            if dist_center < 45 and not is_inside(dx, dz) and not is_stairs(dx, dz):
                if 0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z:

                    # random texture blocks
                    if random.random() < 0.20:
                        t_block = random.choice(ground_textures)
                        editor.placeBlock((x, ground_y - 1, z), Block(t_block))
                        # clear vegetation above (fixes grass/snow sitting on paths)
                        editor.placeBlock((x, ground_y, z), Block("air"))

                # maybe spawn a hut
                if random.random() < 0.02:
                    too_close = False
                    for prev_hut in huts_list:
                        hut_dist = math.sqrt((dx - prev_hut[0])**2 + (dz - prev_hut[1])**2)
                        if hut_dist < 7:
                            too_close = True
                            break

                    if too_close == False:
                        # drill down to find actual solid ground (skip logs, leaves, etc.)
                        hut_y = int(heightmap[hx][hz])
                        while hut_y > -64:
                            try:
                                blk = worldSlice.getBlockGlobal((x, hut_y - 1, z)).id
                                if "log" in blk or "leaves" in blk or "vine" in blk or "bamboo" in blk:
                                    hut_y -= 1
                                else:
                                    break
                            except:
                                break

                        huts_list.append((dx, dz))
                        h_type = random.choice(options)
                        build_hut(x, hut_y, z, h_type, wood, editor, worldSlice)

                        # spawn a few villagers around each hut
                        num_villagers = random.randint(1, 3)
                        for _v in range(num_villagers):
                            v_x = x + random.randint(-1, 1)
                            v_z = z + random.randint(-1, 1)
                            v_y = int(hut_y) + 1
                            editor.runCommandGlobal(
                                f'summon minecraft:villager {v_x} {v_y} {v_z}'
                            )

    print("done! generated", len(huts_list), "huts")

if __name__ == "__main__":
    build_castle()