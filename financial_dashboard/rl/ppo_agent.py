"""
PPO Agent - Proximal Policy Optimization for Trading
=====================================================

Based on AI4Finance-Foundation/FinRL patterns:
- Actor-Critic architecture
- Generalized Advantage Estimation (GAE)
- Gradient clipping
- Learning rate scheduling
- Entropy bonus for exploration
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Check for PyTorch availability
TORCH_AVAILABLE = False
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.distributions import Normal
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("PyTorch not installed. PPO Agent will not be available.")


if TORCH_AVAILABLE:
    
    class ActorCritic(nn.Module):
        """Actor-Critic network for PPO."""
        
        def __init__(
            self,
            state_dim: int,
            action_dim: int,
            hidden_dims: List[int] = None
        ):
            """
            Initialize Actor-Critic network.
            
            Args:
                state_dim: Dimension of state space
                action_dim: Dimension of action space
                hidden_dims: List of hidden layer dimensions
            """
            super().__init__()
            
            hidden_dims = hidden_dims or [256, 256]
            
            # Shared feature extractor
            layers = []
            prev_dim = state_dim
            for hidden_dim in hidden_dims:
                layers.extend([
                    nn.Linear(prev_dim, hidden_dim),
                    nn.LayerNorm(hidden_dim),
                    nn.ReLU(),
                ])
                prev_dim = hidden_dim
            
            self.feature_net = nn.Sequential(*layers)
            
            # Actor (policy) head - outputs action mean
            self.actor_mean = nn.Linear(prev_dim, action_dim)
            
            # Learnable log std for action distribution
            self.actor_log_std = nn.Parameter(torch.zeros(action_dim))
            
            # Critic (value) head
            self.critic = nn.Linear(prev_dim, 1)
            
            # Initialize weights
            self._init_weights()
        
        def _init_weights(self):
            """Orthogonal initialization for stable training."""
            for m in self.modules():
                if isinstance(m, nn.Linear):
                    nn.init.orthogonal_(m.weight, gain=np.sqrt(2))
                    nn.init.zeros_(m.bias)
            
            # Small initialization for actor output
            nn.init.orthogonal_(self.actor_mean.weight, gain=0.01)
        
        def forward(
            self,
            state: torch.Tensor
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """
            Forward pass.
            
            Args:
                state: State tensor
                
            Returns:
                (action_mean, action_std, value)
            """
            features = self.feature_net(state)
            
            # Actor - constrain actions to [-1, 1]
            action_mean = torch.tanh(self.actor_mean(features))
            action_std = torch.exp(self.actor_log_std.clamp(-20, 2))
            
            # Critic
            value = self.critic(features)
            
            return action_mean, action_std, value
        
        def get_action(
            self,
            state: torch.Tensor,
            deterministic: bool = False
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """
            Sample action from policy.
            
            Args:
                state: State tensor
                deterministic: If True, return mean action
                
            Returns:
                (action, log_prob, value)
            """
            action_mean, action_std, value = self.forward(state)
            
            if deterministic:
                return action_mean, torch.zeros_like(action_mean[:, :1]), value
            
            # Sample from normal distribution
            dist = Normal(action_mean, action_std)
            action = dist.sample()
            log_prob = dist.log_prob(action).sum(dim=-1, keepdim=True)
            
            # Clip action to valid range
            action = action.clamp(-1, 1)
            
            return action, log_prob, value
        
        def evaluate_actions(
            self,
            states: torch.Tensor,
            actions: torch.Tensor
        ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            """
            Evaluate actions for given states.
            
            Args:
                states: Batch of states
                actions: Batch of actions
                
            Returns:
                (log_probs, values, entropy)
            """
            action_mean, action_std, values = self.forward(states)
            
            dist = Normal(action_mean, action_std)
            log_probs = dist.log_prob(actions).sum(dim=-1, keepdim=True)
            entropy = dist.entropy().mean()
            
            return log_probs, values, entropy


class RolloutBuffer:
    """Experience buffer for PPO."""
    
    def __init__(self):
        self.states = []
        self.actions = []
        self.log_probs = []
        self.rewards = []
        self.values = []
        self.dones = []
    
    def add(
        self,
        state: np.ndarray,
        action: np.ndarray,
        log_prob: float,
        reward: float,
        value: float,
        done: bool
    ):
        """Add experience to buffer."""
        self.states.append(state)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.values.append(value)
        self.dones.append(done)
    
    def get(self) -> Tuple[np.ndarray, ...]:
        """Get all data from buffer."""
        return (
            np.array(self.states, dtype=np.float32),
            np.array(self.actions, dtype=np.float32),
            np.array(self.log_probs, dtype=np.float32).reshape(-1, 1),
            np.array(self.rewards, dtype=np.float32),
            np.array(self.values, dtype=np.float32),
            np.array(self.dones, dtype=np.float32)
        )
    
    def clear(self):
        """Clear buffer."""
        self.states.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.values.clear()
        self.dones.clear()
    
    def __len__(self):
        return len(self.states)


class PPOAgent:
    """
    Proximal Policy Optimization agent.
    
    Based on FinRL's PPO with improvements:
    - Generalized Advantage Estimation (GAE)
    - Gradient clipping
    - Learning rate scheduling
    - Entropy bonus for exploration
    - Early stopping on KL divergence
    """
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        lr: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_ratio: float = 0.2,
        target_kl: float = 0.01,
        entropy_coef: float = 0.01,
        value_coef: float = 0.5,
        max_grad_norm: float = 0.5,
        n_epochs: int = 10,
        batch_size: int = 64,
        hidden_dims: List[int] = None,
        device: str = None
    ):
        """
        Initialize PPO Agent.
        
        Args:
            state_dim: Dimension of state space
            action_dim: Dimension of action space
            lr: Learning rate
            gamma: Discount factor
            gae_lambda: GAE lambda parameter
            clip_ratio: PPO clip ratio
            target_kl: KL divergence target for early stopping
            entropy_coef: Entropy bonus coefficient
            value_coef: Value loss coefficient
            max_grad_norm: Maximum gradient norm for clipping
            n_epochs: Number of epochs per update
            batch_size: Batch size for updates
            hidden_dims: Hidden layer dimensions
            device: Device to use ('cuda' or 'cpu')
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch is required for PPOAgent")
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_ratio = clip_ratio
        self.target_kl = target_kl
        self.entropy_coef = entropy_coef
        self.value_coef = value_coef
        self.max_grad_norm = max_grad_norm
        self.n_epochs = n_epochs
        self.batch_size = batch_size
        
        # Device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)
        
        # Networks
        self.ac = ActorCritic(
            state_dim,
            action_dim,
            hidden_dims or [256, 256]
        ).to(self.device)
        
        self.optimizer = optim.Adam(self.ac.parameters(), lr=lr)
        
        self.scheduler = optim.lr_scheduler.StepLR(
            self.optimizer,
            step_size=100,
            gamma=0.9
        )
        
        # Experience buffer
        self.buffer = RolloutBuffer()
        
        # Training stats
        self.total_steps = 0
        self.updates = 0
    
    def act(
        self,
        state: np.ndarray,
        deterministic: bool = False
    ) -> Tuple[np.ndarray, float, float]:
        """
        Select action given state.
        
        Args:
            state: Current state
            deterministic: If True, use mean action
            
        Returns:
            (action, log_prob, value)
        """
        state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            action, log_prob, value = self.ac.get_action(state_t, deterministic)
        
        return (
            action.cpu().numpy()[0],
            log_prob.cpu().numpy()[0, 0],
            value.cpu().numpy()[0, 0]
        )
    
    def store_transition(
        self,
        state: np.ndarray,
        action: np.ndarray,
        log_prob: float,
        reward: float,
        value: float,
        done: bool
    ):
        """Store transition in buffer."""
        self.buffer.add(state, action, log_prob, reward, value, done)
        self.total_steps += 1
    
    def compute_gae(
        self,
        rewards: np.ndarray,
        values: np.ndarray,
        dones: np.ndarray,
        last_value: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute GAE returns and advantages.
        
        Args:
            rewards: Array of rewards
            values: Array of values
            dones: Array of done flags
            last_value: Value of final state
            
        Returns:
            (returns, advantages)
        """
        advantages = np.zeros_like(rewards)
        returns = np.zeros_like(rewards)
        
        gae = 0
        next_value = last_value
        
        for t in reversed(range(len(rewards))):
            if dones[t]:
                delta = rewards[t] - values[t]
                gae = delta
            else:
                delta = rewards[t] + self.gamma * next_value - values[t]
                gae = delta + self.gamma * self.gae_lambda * gae
            
            advantages[t] = gae
            returns[t] = advantages[t] + values[t]
            next_value = values[t]
        
        return returns, advantages
    
    def update(self) -> Dict[str, float]:
        """
        Update policy using collected experience.
        
        Returns:
            Dict of training metrics
        """
        if len(self.buffer) == 0:
            return {}
        
        # Get data from buffer
        states, actions, old_log_probs, rewards, values, dones = self.buffer.get()
        
        # Compute GAE
        with torch.no_grad():
            last_state = torch.FloatTensor(states[-1:]).to(self.device)
            _, _, last_value = self.ac(last_state)
            last_value = last_value.cpu().numpy()[0, 0]
        
        returns, advantages = self.compute_gae(rewards, values, dones, last_value)
        
        # Convert to tensors
        states_t = torch.FloatTensor(states).to(self.device)
        actions_t = torch.FloatTensor(actions).to(self.device)
        old_log_probs_t = torch.FloatTensor(old_log_probs).to(self.device)
        returns_t = torch.FloatTensor(returns).to(self.device)
        advantages_t = torch.FloatTensor(advantages).to(self.device)
        
        # Normalize advantages
        advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)
        
        # PPO update
        policy_losses = []
        value_losses = []
        entropy_losses = []
        kl_divs = []
        
        n_samples = len(states)
        
        for epoch in range(self.n_epochs):
            # Shuffle indices
            indices = np.random.permutation(n_samples)
            
            for start in range(0, n_samples, self.batch_size):
                end = min(start + self.batch_size, n_samples)
                batch_indices = indices[start:end]
                
                # Get batch
                batch_states = states_t[batch_indices]
                batch_actions = actions_t[batch_indices]
                batch_old_log_probs = old_log_probs_t[batch_indices]
                batch_returns = returns_t[batch_indices]
                batch_advantages = advantages_t[batch_indices]
                
                # Evaluate actions
                new_log_probs, values_pred, entropy = self.ac.evaluate_actions(
                    batch_states, batch_actions
                )
                
                # Policy loss (clipped surrogate)
                ratio = torch.exp(new_log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages.unsqueeze(1)
                surr2 = torch.clamp(
                    ratio,
                    1 - self.clip_ratio,
                    1 + self.clip_ratio
                ) * batch_advantages.unsqueeze(1)
                policy_loss = -torch.min(surr1, surr2).mean()
                
                # Value loss
                value_loss = nn.functional.mse_loss(
                    values_pred.squeeze(),
                    batch_returns
                )
                
                # Total loss
                loss = (
                    policy_loss
                    + self.value_coef * value_loss
                    - self.entropy_coef * entropy
                )
                
                # Backward pass
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.ac.parameters(), self.max_grad_norm)
                self.optimizer.step()
                
                # Logging
                policy_losses.append(policy_loss.item())
                value_losses.append(value_loss.item())
                entropy_losses.append(entropy.item())
                
                # KL divergence
                with torch.no_grad():
                    kl = (batch_old_log_probs - new_log_probs).mean().item()
                    kl_divs.append(kl)
            
            # Early stopping on KL
            if np.mean(kl_divs[-10:]) > self.target_kl:
                logger.debug(f"Early stopping at epoch {epoch} due to KL divergence")
                break
        
        # Update scheduler
        self.scheduler.step()
        self.updates += 1
        
        # Clear buffer
        self.buffer.clear()
        
        return {
            'policy_loss': np.mean(policy_losses),
            'value_loss': np.mean(value_losses),
            'entropy': np.mean(entropy_losses),
            'kl_divergence': np.mean(kl_divs),
            'learning_rate': self.scheduler.get_last_lr()[0]
        }
    
    def save(self, path: str):
        """Save model checkpoint."""
        torch.save({
            'ac_state_dict': self.ac.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'total_steps': self.total_steps,
            'updates': self.updates
        }, path)
        logger.info(f"Model saved to {path}")
    
    def load(self, path: str):
        """Load model checkpoint."""
        checkpoint = torch.load(path, map_location=self.device)
        self.ac.load_state_dict(checkpoint['ac_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.total_steps = checkpoint.get('total_steps', 0)
        self.updates = checkpoint.get('updates', 0)
        logger.info(f"Model loaded from {path}")


def train_ppo(
    env,
    agent: 'PPOAgent',
    total_timesteps: int = 100000,
    update_timesteps: int = 2048,
    eval_freq: int = 10000,
    eval_env=None,
    verbose: int = 1
) -> Dict:
    """
    Train PPO agent on environment.
    
    Args:
        env: Training environment
        agent: PPO agent
        total_timesteps: Total training timesteps
        update_timesteps: Timesteps between updates
        eval_freq: Evaluation frequency
        eval_env: Evaluation environment
        verbose: Verbosity level
        
    Returns:
        Training history
    """
    history = {
        'timesteps': [],
        'rewards': [],
        'policy_loss': [],
        'value_loss': [],
        'eval_rewards': []
    }
    
    state, _ = env.reset()
    episode_reward = 0
    episode_rewards = []
    
    for step in range(total_timesteps):
        # Get action
        action, log_prob, value = agent.act(state)
        
        # Step environment
        next_state, reward, done, truncated, info = env.step(action)
        
        # Store transition
        agent.store_transition(state, action, log_prob, reward, value, done or truncated)
        
        episode_reward += reward
        state = next_state
        
        # Episode done
        if done or truncated:
            episode_rewards.append(episode_reward)
            episode_reward = 0
            state, _ = env.reset()
        
        # Update agent
        if (step + 1) % update_timesteps == 0:
            update_info = agent.update()
            
            history['timesteps'].append(step + 1)
            history['rewards'].append(np.mean(episode_rewards[-10:]) if episode_rewards else 0)
            history['policy_loss'].append(update_info.get('policy_loss', 0))
            history['value_loss'].append(update_info.get('value_loss', 0))
            
            if verbose > 0:
                avg_reward = np.mean(episode_rewards[-10:]) if episode_rewards else 0
                logger.info(
                    f"Step {step+1}: avg_reward={avg_reward:.4f}, "
                    f"policy_loss={update_info.get('policy_loss', 0):.4f}, "
                    f"value_loss={update_info.get('value_loss', 0):.4f}"
                )
        
        # Evaluation
        if eval_env is not None and (step + 1) % eval_freq == 0:
            eval_reward = evaluate_agent(agent, eval_env)
            history['eval_rewards'].append(eval_reward)
            
            if verbose > 0:
                logger.info(f"Evaluation reward: {eval_reward:.4f}")
    
    return history


def evaluate_agent(agent: 'PPOAgent', env, n_episodes: int = 1) -> float:
    """Evaluate agent on environment."""
    total_rewards = []
    
    for _ in range(n_episodes):
        state, _ = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            action, _, _ = agent.act(state, deterministic=True)
            state, reward, done, truncated, _ = env.step(action)
            episode_reward += reward
            done = done or truncated
        
        total_rewards.append(episode_reward)
    
    return np.mean(total_rewards)
