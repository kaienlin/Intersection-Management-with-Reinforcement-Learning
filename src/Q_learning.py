import random
import sys, time, os, pickle
import numpy as np
import matplotlib.pyplot as plt
from typing import Iterable

from environment import GraphBasedSimEnv
from simulator import Intersection, Simulator

from utility import get_4cz_intersection
from traffic_gen import random_traffic_generator, enumerate_traffic_patterns_generator

def load_Q_table(env):
    if os.path.exists("./Q.npy"):
        return np.load("./Q.npy")
    else:
        return np.zeros((env.observation_space.n, env.action_space.n))

def save_Q_table(Q):
    np.save("./Q.npy", Q)

def train_Q(env, Q, seen_state=None, alpha=0.1, gamma=1.0, epsilon=0.5):
    done = False
    state = env.reset()
    if seen_state is not None:
        seen_state.add(state)
    cost_sum = 0
    
    while not done:
        # epsilon-greedy
        if random.uniform(0, 1) < epsilon:
            action = random.randint(0, env.action_space_size - 1)
        else:
            action = np.argmin(Q[state])

        # take action
        next_state, cost, done, _ = env.step(action)
        cost_sum += cost

        # update Q table
        next_min = np.min(Q[next_state])
        Q[state, action] = (1 - alpha) * Q[state, action] + alpha * (cost + gamma * next_min)

        state = next_state
        if seen_state is not None:
            seen_state.add(state)
    
    return cost_sum

def evaluate_Q(env, Q):
    done = False
    state = env.reset()
    cost_sum = 0

    trap_state = state
    trap_state_counter = 0
    while not done:
        action = np.argmin(Q[state])
        state, cost, done, _ = env.step(action)
        cost_sum += cost
        if state == trap_state:
            trap_state_counter += 1
            if trap_state_counter == 500:
                cost_sum += 1000000000
                break
        else:
            trap_state = state
    print(f"  * Q-learning: {cost_sum}")

    done = False
    state = env.reset()
    cost_sum = 0
    while not done:
        # Greedy Scheduler
        action = 0
        dec = env.decode_state(state)
        for pos in dec["vehicle_positions"]:
            if not pos["waiting"]:
                continue
            if pos["type"] == "src":
                action = env.encode_action(pos["id"], is_cz=False)
                break
            elif pos["type"] == "cz":
                action = env.encode_action(pos["id"], is_cz=True)
                break
        state, cost, done, _ = env.step(action)
        cost_sum += cost
    print(f"  * Greedy: {cost_sum}")
            

def Q_learning(simulator_generator: Iterable[Simulator]):
    num_evaluation_epoch = 1

    # create simulator and environment
    sim = next(simulator_generator)
    env = GraphBasedSimEnv(sim)

    Q = load_Q_table(env)
    seen_state = pickle.load(open("seen.p", "rb")) if os.path.exists("seen.p") else set()

    #for epoch in range(num_training_epoch):
    epoch = 0
    while True:
        print(f"epoch = {epoch}: {len(seen_state)} / {env.observation_space.n} states explored")
        train_Q(env, Q, seen_state)
        
        if (epoch + 1) % 10 == 0:
            try:
                sim = next(simulator_generator)
            except StopIteration:
                break
            env = GraphBasedSimEnv(sim)

        if (epoch + 1) % 10000 == 0:
            save_Q_table(Q)
            pickle.dump(seen_state, open("seen.p", "wb"))
        epoch += 1

    save_Q_table(Q)
    pickle.dump(seen_state, open("seen.p", "wb"))

    # Evaluation
    random_sim_gen = random_traffic_generator(intersection, num_iter=num_evaluation_epoch)
    for sim in random_sim_gen:
        env = GraphBasedSimEnv(sim)
        evaluate_Q(env, Q)      


if __name__ == "__main__":
    seed = 12245
    random.seed(seed)
    np.random.seed(seed)
    intersection = get_4cz_intersection()
    sim_gen = enumerate_traffic_patterns_generator(intersection)
    Q_learning(sim_gen)

