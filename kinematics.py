import numpy as np
from constants import *


def computeDK(theta1, theta2, theta3):
    """ Compute the direct kinematics of the end point of one leg of the robot."""
    return computeDKDetailed(theta1, theta2, theta3)[0]


def computeDKDetailed(theta1, theta2, theta3):
    """
    Compute the direct kinematics of 3 points of one leg of the robot.
    :param theta1: Angle of the first joint of the leg.
    :param theta2: Angle of the second joint of the leg.
    :param theta3: Angle of the third joint of the leg.
    :return: array of positions
    """
    theta1 = THETA1_MOTOR_SIGN * theta1
    theta2 = THETA2_MOTOR_SIGN * theta2 - theta2Correction
    theta3 = THETA3_MOTOR_SIGN * theta3 - theta3Correction
    O = np.array([[0], [0], [0]])
    # point A
    A = np.array([constL1 * np.cos(theta1), constL1 * np.sin(theta1), 0])

    # point B
    B = np.dot(rotation_matrixZ(theta1),
               np.array([constL2 * np.cos(- theta2), 0, constL2 * np.sin(- theta2)])) + A

    # point C
    C = np.dot(rotation_matrixZ(theta1), np.dot(rotation_matrixY(theta2 + np.pi),
                                                np.array([constL3 * np.cos(np.pi - theta3), 0,
                                                          constL3 * np.sin(np.pi - theta3)]))) + B

    return O, A, B, C


def alkashi(a, b, c, sign=-1):
    """ Compute AlKashi angle from 3 sides taking the sign into account. """
    if a == 0 or b == 0:
        return 0
    return sign * math.acos(min(1, max(-1, (a ** 2 + b ** 2 - c ** 2) / (2 * a * b))))


def modulo_angle(angle):
    """ Return the angle in the range [-pi, pi] or [-180, 180] depending on constant.py USE_RADS_INPUT."""
    if USE_RADS_INPUT:
        borne = math.pi
    else:
        borne = 180

    if -borne < angle < borne:
        return angle
    angle = angle % (borne * 2)
    if angle > borne:
        return -borne * 2 + angle
    return angle


def computeIK(x, y, z):
    """ Compute the inverse kinematics of the first leg of the robot. """
    if USE_MM_INPUT:
        x = x * 1000
        y = y * 1000
        z = z * 1000

    if y == 0 or x == 0:
        theta1 = 0
    else:
        theta1 = np.arctan2(y, x)
    ax, ay = constL1 * np.cos(theta1), constL1 * np.sin(theta1)

    ac = math.sqrt((x - ax) ** 2 + (y - ay) ** 2 + z ** 2)
    theta2 = (alkashi(ac, constL2, constL3) - Z_DIRECTION * np.arcsin(z / ac) + theta2Correction) * THETA2_MOTOR_SIGN
    theta3 = (np.pi + alkashi(constL2, constL3, ac) + theta3Correction) * THETA3_MOTOR_SIGN

    if not USE_RADS_INPUT:
        theta1 = math.degrees(theta1)
        theta2 = math.degrees(theta2)
        theta3 = math.degrees(theta3)

    theta1 = modulo_angle(theta1)
    theta2 = modulo_angle(theta2)
    theta3 = modulo_angle(theta3)

    # print("theta1: ", theta1, "theta2: ", theta2, "theta3: ", theta3)
    return [theta1, theta2, theta3]


def rotaton_2D(x, y, z, angle):
    """ Rotate a point about a z axe rotation of angle. """
    return np.dot(rotation_matrixZ(angle), np.array([x, y, z]))


def computeIKOriented(x, y, z, leg_id, params):
    """ Compute the inverse kinematics of the asked leg of the robot. """
    res = rotation_matrixZ(LEG_ANGLES[leg_id - 1]) @ np.array([x, y, z]) + (params.initLeg[leg_id - 1] + [params.z])
    # print("res: ", res)
    return computeIK(*res)


def rotation_matrixX(theta):
    return np.array([[1, 0, 0], [0, np.cos(theta), -np.sin(theta)], [0, np.sin(theta), np.cos(theta)]])


def rotation_matrixY(theta):
    return np.array([[np.cos(theta), 0, np.sin(theta)], [0, 1, 0], [-np.sin(theta), 0, np.cos(theta)]])


def rotation_matrixZ(theta):
    return np.array([[np.cos(theta), -np.sin(theta), 0], [np.sin(theta), np.cos(theta), 0], [0, 0, 1]])


def interpolate(values, t):
    """
    Interpolate the values at time t.
    :param values: a list of values
    :param t: a time
    :return: the interpolated value
    """
    for i in range(len(values) - 1):
        if values[i][0] <= t <= values[i + 1][0]:
            return values[i][1] + (t - values[i][0]) * (values[i + 1][1] - values[i][1]) / (
                    values[i + 1][0] - values[i][0])
    if len(values) == 1:
        return 0
    else:
        return np.array([0, 0, 0])


def walk(t, speed_x, speed_y, params):
    """
    Hexapode translation walk.
    :return: The 18 motors angles asked at the time t.
    """
    allLegs = np.array([[0.0, 0.0, 0.0] for i in range(6)])
    res = []
    for i in range(6):
        v = [(0, np.array([allLegs[i][0], allLegs[i][1], allLegs[i][2]])),
             (0.25, np.array([allLegs[i][0] + 0.2 * speed_x, allLegs[i][1] + 0.2 * speed_y,
                              allLegs[i][2] + 0.05 * 3 * (abs(speed_x) + abs(speed_y))])),
             (0.5, np.array([allLegs[i][0] + 0.4 * speed_x, allLegs[i][1] + 0.4 * speed_y, allLegs[i][2]])),
             (1, np.array([allLegs[i][0], allLegs[i][1], allLegs[i][2]]))]
        if i == 1 or i == 3 or i == 5:
            time = t % 1
        else:
            time = (t + 0.5) % 1
        x, y, z = interpolate(v, time)
        print(x, y, z)
        alphas = computeIKOriented(x, y, z, i + 1, params)
        # alphas = [math.degrees(alpha) for alpha in alphas]
        res += [alphas]
    return res


def rotate(t, omega, params, direction=1):
    """
    Hexapode rotation around itself.
    :return: the 18 motors angles asked at the time t.
    """
    allLegs = np.array([[0.0, 0.0, 0.0] for i in range(6)])
    res = []
    for i in range(6):

        # Passage du référentiel du bout de la patte à celui du début de la patte pour calculer le point cible
        angles = computeIKOriented(0, 0, 0, i + 1, params)
        O, A, B, C = computeDKDetailed(angles[0], angles[1], angles[2])
        rot = rotaton_2D(*C, omega * direction)

        # Retour au bon référentiel + correction dû au fait que la rotation est centrée sur la patte et non sur le robot
        rot = rot - C + [0.01/0.2 * omega * direction, 0.2/0.2 * omega * direction, 0] @ rotation_matrixZ(LEG_ANGLES[i])

        # Calcul de la position cible
        v = [(0, np.array([0, 0, 0])),
             (0.25, np.array([rot[0] / 2, rot[1] / 2,
                              rot[2] + 0.5 * omega])),
             (0.5, np.array([rot[0], rot[1], 0])),
             (1, np.array([0, 0, 0]))]

        # Séparation des 6 patte en 2 groupes de 3
        if i == 0 or i == 2 or i == 4:
            time = t % 1
        else:
            time = (t + 0.5) % 1

        # Interpolation
        x, y, z = interpolate(v, time)

        # Cinématique inverse orienté
        alphas = computeIKOriented(x, y, z, i + 1, params)
        res += [alphas]
    return res


def holonomic(t, speed_x, speed_y, omega, direction, params):
    """
    Hexapode holonomic movement, combining translation and rotation.
    :return: the 18 motors angles asked at the time t.
    """
    # Initialisation des positions des 6 pattes
    allLegs = np.array([[0.0, 0.0, 0.0] for i in range(6)])
    res = []
    for i in range(6):
        # Calcul de la position cible pour la rotation
        angles = computeIKOriented(0, 0, 0, i + 1, params)
        # print("angles :", angles)
        O, A, B, C = computeDKDetailed(angles[0], angles[1], angles[2])
        # print("x, y, z :", C)
        rot = rotaton_2D(*C, omega * direction)
        # print("rot : ", *rot)
        rot = rot - C + [0.01 / 0.2 * omega * direction, 0.2 / 0.2 * omega * direction, 0] @ rotation_matrixZ(
            LEG_ANGLES[i])
        # print("rot good ref :", *rot)
        v1 = [(0, np.array([0, 0, 0])),
             (0.25, np.array([rot[0] / 2, rot[1] / 2,
                              rot[2] + 0.5 * omega])),
             (0.5, np.array([rot[0], rot[1], 0])),
             (1, np.array([0, 0, 0]))]

        # Calcul de la position cible pour la translation
        v2 = [(0, np.array([allLegs[i][0], allLegs[i][1], allLegs[i][2]])),
             (0.25, np.array([allLegs[i][0] + 0.2 * speed_x, allLegs[i][1] + 0.2 * speed_y,
                              allLegs[i][2] + 0.05 * 3 * (abs(speed_x) + abs(speed_y))])),
             (0.5, np.array([allLegs[i][0] + 0.4 * speed_x, allLegs[i][1] + 0.4 * speed_y, allLegs[i][2]])),
             (1, np.array([allLegs[i][0], allLegs[i][1], allLegs[i][2]]))]

        # Séparation des 6 patte en 2 groupes de 3 et moyenne des interpolations
        if i == 1 or i == 3 or i == 5:
            time = t % 1
        else:
            time = (t + 0.5) % 1
        x1, y1, z1 = interpolate(v1, time)
        x2, y2, z2 = interpolate(v2, time)
        x, y, z = (x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2

        # Cinématique inverse orienté
        alphas = computeIKOriented(x, y, z, i + 1, params)
        res += [alphas]
    return res
