import gymnasium as gym

from ray.rllib.core.models.catalog import Catalog
from ray.rllib.core.models.configs import ActorCriticEncoderConfig, MLPHeadConfig
from ray.rllib.utils import override


class PPOCatalog(Catalog):
    """The Catalog class used to build models for PPO.

    PPOCatalog provides the following models:
        - ActorCriticEncoder: The encoder used to encode the observations.
        - Pi Head: The head used to compute the policy logits.
        - Value Function Head: The head used to compute the value function.

    The ActorCriticEncoder is a wrapper around Encoders to produce separate outputs
    for the policy and value function. See implementations of PPORLModuleBase for
    more details.

    Any custom ActorCriticEncoder can be built by overriding the
    build_actor_critic_encoder() method. Alternatively, the ActorCriticEncoderConfig
    at PPOCatalog.actor_critic_encoder_config can be overridden to build a custom
    ActorCriticEncoder during RLModule runtime.

    Any custom head can be built by overriding the build_pi_head() and build_vf_head()
    methods. Alternatively, the PiHeadConfig and VfHeadConfig can be overridden to
    build custom heads during RLModule runtime.
    """

    def __init__(
        self,
        observation_space: gym.Space,
        action_space: gym.Space,
        model_config_dict: dict,
    ):
        """Initializes the PPOCatalog.

        Args:
            observation_space: The observation space of the Encoder.
            action_space: The action space for the Pi Head.
            model_config_dict: The model config to use.
        """
        super().__init__(
            observation_space=observation_space,
            action_space=action_space,
            model_config_dict=model_config_dict,
        )
        free_log_std = model_config_dict.get("free_log_std")
        assert not free_log_std, "free_log_std not supported yet."

        assert isinstance(
            observation_space, gym.spaces.Box
        ), "This simple PPO Module only supports Box observation space."

        assert len(observation_space.shape) in (
            1,
        ), "This simple PPO Module only supports 1D observation spaces."

        assert isinstance(action_space, (gym.spaces.Discrete, gym.spaces.Box)), (
            "This simple PPO Module only supports Discrete and Box action spaces.",
        )

        # Replace EncoderConfig by ActorCriticEncoderConfig
        self.actor_critic_encoder_config = ActorCriticEncoderConfig(
            base_encoder_config=self.encoder_config,
            shared=self.model_config_dict["vf_share_layers"],
        )

        if isinstance(action_space, gym.spaces.Discrete):
            pi_output_dim = action_space.n
        else:
            pi_output_dim = action_space.shape[0] * 2

        post_fcnet_hiddens = self.model_config_dict["post_fcnet_hiddens"]
        post_fcnet_activation = self.model_config_dict["post_fcnet_activation"]

        self.pi_head_config = MLPHeadConfig(
            input_dim=self.encoder_config.output_dim,
            hidden_layer_dims=post_fcnet_hiddens,
            hidden_layer_activation=post_fcnet_activation,
            output_activation="linear",
            output_dim=pi_output_dim,
        )

        self.vf_head_config = MLPHeadConfig(
            input_dim=self.encoder_config.output_dim,
            hidden_layer_dims=post_fcnet_hiddens,
            hidden_layer_activation=post_fcnet_activation,
            output_activation="linear",
            output_dim=1,
        )

        # Set input- and output dimensions to fit PPO's needs.
        self.encoder_config.input_dim = observation_space.shape[0]
        self.pi_head_config.input_dim = self.encoder_config.output_dim
        if isinstance(action_space, gym.spaces.Discrete):
            self.pi_head_config.output_dim = int(action_space.n)
        else:
            self.pi_head_config.output_dim = int(action_space.shape[0] * 2)
        self.vf_head_config.output_dim = 1

    def build_actor_critic_encoder(self, framework: str):
        """Builds the ActorCriticEncoder.

        The default behavior is to build the encoder from the encoder_config.
        This can be overridden to build a custom ActorCriticEncoder as a means of
        configuring the behavior of a PPORLModuleBase implementation.

        Args:
            framework: The framework to use. Either "torch" or "tf".

        Returns:
            The ActorCriticEncoder.
        """
        return self.actor_critic_encoder_config.build(framework=framework)

    @override(Catalog)
    def build_encoder(self, framework: str):
        """Builds the encoder.

        Since PPO uses an ActorCriticEncoder, this method should not be implemented.
        """
        raise NotImplementedError(
            "Use PPOCatalog.build_actor_critic_encoder() instead."
        )

    def build_pi_head(self, framework: str):
        """Builds the policy head.

        The default behavior is to build the head from the pi_head_config.
        This can be overridden to build a custom policy head as a means of configuring
        the behavior of a PPORLModuleBase implementation.

        Args:
            framework: The framework to use. Either "torch" or "tf".

        Returns:
            The policy head.
        """
        return self.pi_head_config.build(framework=framework)

    def build_vf_head(self, framework: str):
        """Builds the value function head.

        The default behavior is to build the head from the vf_head_config.
        This can be overridden to build a custom value function head as a means of
        configuring the behavior of a PPORLModuleBase implementation.

        Args:
            framework: The framework to use. Either "torch" or "tf".

        Returns:
            The value function head.
        """
        return self.vf_head_config.build(framework=framework)
