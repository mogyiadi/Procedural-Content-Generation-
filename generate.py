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
    if dx >= -3 and dx <= 3 and dz >= 31 and dz <= 40:
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
                block_id = worldSlice.getBlock((x, ground_y, z)).id
                if "log" in block_id or "leaves" in block_id or "vine" in block_id:
                    ground_y -= 1
                else:
                    break
        else:
            ground_y = 64
            
        base_y = ground_y
        
        # stop walls going too deep in ravines
        if prev_y is not None:
            if prev_y - ground_y > 10: 
                base_y = prev_y 
            elif ground_y - prev_y > 10: 
                base_y = ground_y
                
        wall_bases.append((x, base_y, z))
        prev_y = base_y
        
    gate_cx = cx
    gate_cz = cz + radius
    
    print("building walls and gate...")
    for w in wall_bases:
        x = w[0]
        base_y = w[1]
        z = w[2]
        
        dist_gate = math.sqrt((x - gate_cx)**2 + (z - gate_cz)**2)
        if dist_gate <= 4:
            for y in range(base_y, base_y + wall_height):
                if dist_gate <= 2 and y < base_y + 5:
                    editor.placeBlock((x, y, z), Block("air"))
                else:
                    editor.placeBlock((x, y, z), Block(f"{wood}_log", {"axis": "y"}))
        else:
            for y in range(base_y, base_y + wall_height):
                editor.placeBlock((x, y, z), get_random_wall_block())
            for fy in range(base_y - 1, base_y - 15, -1):
                editor.placeBlock((x, fy, z), get_random_wall_block())
            # little crenellations
            if random.random() < 0.5:
                editor.placeBlock((x, base_y + wall_height, z), get_random_wall_block())

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
                local_ground = int(heightmap[hx][hz]) if (0 <= hx < buildArea.size.z and 0 <= hz < buildArea.size.z) else center_y

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
    for step in range(10):
        sz = 31 + step
        sy = keep_base_y - 1 - step
        for sx in range(-3, 4):
            x = cx + sx
            z = cz + sz
            if abs(sx) <= 2:
                editor.placeBlock((x, sy, z), Block("stone_brick_stairs", {"facing": "north"}))
                # fill under stairs
                hx, hz = x - buildArea.begin.x, z - buildArea.begin.z
                local_ground = int(heightmap[hx][hz]) if (0 <= hx < buildArea.size.x and 0 <= hz < buildArea.size.z) else center_y
                for fy in range(local_ground - 5, sy):
                    editor.placeBlock((x, fy, z), Block("stone_bricks"))
                # clear air 
                for ay in range(sy + 1, sy + 5):
                    editor.placeBlock((x, ay, z), Block("air"))
            else:
                editor.placeBlock((x, sy + 1, z), get_random_wall_block())
                for fy in range(center_y, sy + 1):
                    editor.placeBlock((x, fy, z), get_random_wall_block())

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
                if hx >= 0 and hx < buildArea.size.x and hz >= 0 and hz < buildArea.size.z:

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