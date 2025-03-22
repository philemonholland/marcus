import numpy as np

def compute_angles_y(Input_Angle):

    Angle_input = -np.deg2rad(Input_Angle)
    
    wx = np.array([1, 0, 0])
    r_w_O0wS0 = np.array([53.5, -45, 0])
    r_o_O0wA0 = np.array([82, 2, 0])
    
    wRo = np.array([
        [np.cos(-Angle_input), np.sin(-Angle_input), 0],
        [-np.sin(-Angle_input), np.cos(-Angle_input), 0],
        [0, 0, 1]
    ])
    
    r_w_O0wA0 = wRo @ r_o_O0wA0
    
    cross_product_wx_A0 = np.cross(wx, r_w_O0wA0)
    Angle_w_O0wA0 = np.arctan2(
        np.sign(cross_product_wx_A0[2]) * np.linalg.norm(cross_product_wx_A0),
        np.dot(wx, r_w_O0wA0)
    )
    
    r_w_A0wS0 = r_w_O0wS0 - r_w_O0wA0
    norm_r_w_A0wS0 = np.linalg.norm(r_w_A0wS0)
    
    cross_product_A0_S0 = np.cross(r_w_O0wA0, r_w_A0wS0)
    Angle_w_S0wA0 = Angle_w_O0wA0 + np.arctan2(
        np.sign(cross_product_A0_S0[2]) * np.linalg.norm(cross_product_A0_S0),
        np.dot(r_w_O0wA0, r_w_A0wS0)
    )
    
    Angle_o_S0wA0_deg = np.rad2deg(Angle_w_S0wA0)
    
    r_b_A0wB0 = np.array([40, 0, 0])
    norm_r_o_A0wB0 = np.linalg.norm(r_b_A0wB0)
    
    r_c_B0wC0 = np.array([40, 0, 0])
    norm_r_o_B0wC0 = np.linalg.norm(r_c_B0wC0)
    
    angle_lois_cosinus = np.arccos(
        (norm_r_o_B0wC0**2 - norm_r_o_A0wB0**2 - norm_r_w_A0wS0**2) /
        (-2 * norm_r_o_A0wB0 * norm_r_w_A0wS0)
    )
    
    Angle_w_A0wB0 = Angle_w_S0wA0 + angle_lois_cosinus
    
    angle_lois_cosinus = np.arccos(
        (norm_r_w_A0wS0**2 - norm_r_o_A0wB0**2 - norm_r_o_B0wC0**2) /
        (-2 * norm_r_o_A0wB0 * norm_r_o_B0wC0)
    )
    
    Angle_w_S0wC0 = Angle_w_A0wB0 + angle_lois_cosinus

    Angle_servo = np.rad2deg(Angle_w_S0wC0)

    if(Angle_servo > 180):
        Angle_servo -= 360
    
    return Angle_servo



def compute_angles_paupiere(Input_Angle):
    Angle = np.pi / 2 - np.deg2rad(Input_Angle)
    
    wRa = np.array([
        [np.sin(Angle), np.cos(Angle), 0],
        [-np.cos(Angle), np.sin(Angle), 0],
        [0, 0, 1]
    ])
    
    Angle_w_A0wB0 = np.deg2rad(46.95295747)
    
    aRb = np.array([
        [np.cos(Angle_w_A0wB0), -np.sin(Angle_w_A0wB0), 0],
        [np.sin(Angle_w_A0wB0), np.cos(Angle_w_A0wB0), 0],
        [0, 0, 1]
    ])
    
    r_b_W0wB0 = np.array([20.651876, 0, 0])
    
    r_w_W0wB0 = wRa @ aRb @ r_b_W0wB0
    
    r_w_W0wE0 = np.array([62.75, 18.5, 0])
    
    r_w_B0wE0 = r_w_W0wE0 - r_w_W0wB0
    
    norm_r_w_B0wE0 = np.linalg.norm(r_w_B0wE0)
    norm_r_w_B0wC0 = 48
    norm_r_w_C0wE0 = 54.378305
    
    wx = np.array([1, 0, 0])
    
    cross_product_wx_E0 = np.cross(wx, r_w_B0wE0)
    Angle_w_W0wB0 = np.arctan2(
        np.sign(cross_product_wx_E0[2]) * np.linalg.norm(cross_product_wx_E0), 
        np.dot(wx, r_w_B0wE0)
    )
    
    a, b, c = norm_r_w_B0wE0, norm_r_w_B0wC0, norm_r_w_C0wE0
    
    C = np.arccos((c**2 - a**2 - b**2) / (-2 * a * b))
    A = np.arccos((a**2 - c**2 - b**2) / (-2 * c * b))
    
    Angle_w_B0wC0 = Angle_w_W0wB0 - C
    Angle_w_C0wE0 = np.pi + Angle_w_B0wC0 - A
    
    r_w_C0wE0 = np.array([46, 29, 0])
    
    Angle_c_C0wE0 = np.arctan(r_w_C0wE0[1] / r_w_C0wE0[0])
    
    Angle_servo = Angle_w_C0wE0 - Angle_c_C0wE0
    
    return np.rad2deg(Angle_servo)

def compute_angles_x(Input_Angle):
    a = 43
    c = 77.5
    
    B = -np.deg2rad(Input_Angle)
    
    b = np.sqrt(a**2 + c**2 - 2 * a * c * np.cos(B))
    
    A = np.arcsin((a * np.sin(B)) / b)

    Angle_servo = A
    
    return np.rad2deg(Angle_servo)

# Define step size
angle_step = 0.1  # Step size

# Run loop and save to file
with open("angles_output.txt", "w") as file:
    for angle in np.arange(-45.0, 45.1, angle_step):
        result = compute_angles_paupiere(angle) # Change this line to test different functions
        file.write(f"Angle: {angle:.1f}, Result: {result:.6f}\n")

print("Computation complete. Results saved in 'angles_output.txt'.")
