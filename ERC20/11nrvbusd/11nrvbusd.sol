/**
 *Submitted for verification at BscScan.com on 2021-04-25
*/

// SPDX-License-Identifier: MIT

// Eleven.finance vault erc20

pragma solidity ^0.8.0;

import "../../../openzeppelin/contracts/token/ERC20/ERC20.sol";
import "../../../openzeppelin/contracts/access/Ownable.sol";
import "../../../openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "../../../openzeppelin/contracts/token/ERC20/IERC20.sol";
import "../../../openzeppelin/contracts/utils/Context.sol";
import "../../../openzeppelin/contracts/utils/Address.sol";


interface IMasterMind {
    function deposit(uint256 _pid, uint256 _amount) external;
    function withdraw(uint256 _pid, uint256 _amount) external;
    function enterStaking(uint256 _amount) external;
    function leaveStaking(uint256 _amount) external;
    function pendingNerve(uint256 _pid, address _user) external view returns (uint256);
    function userInfo(uint256 _pid, address _user) external view returns (uint256, uint256);
    function emergencyWithdraw(uint256 _pid) external;
}


interface IPendingEle{
    function pendingEleven(uint256 _pid, address _user) external view returns (uint256);
}

interface Buybackstrat{
    function chargeFees(address, address) external;
}


interface ConvertTo11NrvStrat{
    function convert(address _token) external;
}

interface Pps{
    function getPricePerFullShare() external view returns (uint256);
}

/**
 * @dev Implementation of a vault to deposit funds for yield optimizing.
 * This is the contract that receives funds and that users interface with.
 * The yield optimizing strategy itself is implemented in a separate 'Strategy.sol' contract.
 */
contract ElevenNeverSellVault is ERC20, Ownable {
    using SafeERC20 for IERC20;
    using Address for address;

    // The token the vault accepts and looks to maximize.
    IERC20 public token;
    event Deposited(address user, uint amount, uint block);
    event Withdrawn(address user, uint amount, uint block);
    
    /**
     * @dev Sets the value of {token} to the token that the vault will
     * hold as underlying value. It initializes the vault's own 'moo' token.
     * This token is minted when someone does a deposit. It is burned in order
     * to withdraw the corresponding portion of the underlying assets.
     */
     
    address constant public mastermind = 0x2EBe8CDbCB5fB8564bC45999DAb8DA264E31f24E;
    address constant public elechef = 0x1ac6C0B955B6D7ACb61c9Bdf3EE98E0689e07B8A;
    address constant public nrv = 0x42F6f551ae042cBe50C739158b4f0CAC0Edb9096;
    address constant public xnrv = 0x15B9462d4Eb94222a7506Bc7A25FB27a2359291e;
    address constant public nrv11 = 0x54f4D5dd6164B99603E77C8E13FFC3B239F63147;
    address constant public ele = 0xAcD7B3D9c10e97d0efA418903C0c7669E702E4C0;
    uint constant nrvPid = 7;
    uint public elePid;
    address dummyAddress;
    uint public bpsFee = 150;
    address public buybackstrat;
    address public convertTo11nrvStrat;
    uint public harvested11nrvPerShare;
    mapping(address => uint) public harvested11nrvPerUser;
    uint public harvestedElePerShare;
    mapping(address => uint) public harvestedElePerUser;
    mapping(address => bool) public harvesters;
    
    constructor() ERC20("11nrvbusd", "11 nrvbusd lp Nerve") Ownable(msg.sender) {
        token = IERC20(0x401479091d0F7b8AE437Ee8B054575cd33ea72Bd);
        token.approve(mastermind, type(uint256).max);
    }

    function setHarvestor(address _add, bool _bool) onlyOwner external{
        harvesters[_add] = _bool;
    }
    
    function setDummyToken(address _add, uint _pid) onlyOwner external{
        dummyAddress = _add;
        elePid = _pid;
        IERC20(_add).approve(elechef, type(uint256).max);
        IMasterMind(elechef).deposit(_pid, IERC20(_add).balanceOf(address(this)));
    }
    
    bool testing = true;
    
    function disableTesting() onlyOwner external{
        testing = false;
    }
    
    function recoverDummy() onlyOwner external{
        require(testing, "not allowed");
        IMasterMind(elechef).emergencyWithdraw(elePid);
        IERC20(dummyAddress).transfer(msg.sender, IERC20(dummyAddress).balanceOf(address(this)));
    }
    
    function setBuybackStrat(address _add) onlyOwner external{
        buybackstrat = _add;
    }

    function setConvertStrat(address _add) onlyOwner external{
        convertTo11nrvStrat = _add;
    }
    
    function changeBpsFee(uint _fee) onlyOwner external{
        require(_fee<250, "too much fee");
        bpsFee = _fee;
    }
    
    function balance() public view returns (uint) {
        return available() + insideChef();
    }

    /**
     * @dev Custom logic in here for how much the vault allows to be borrowed.
     * We return 100% of tokens for now. Under certain conditions we might
     * want to keep some of the system funds at hand in the vault, instead
     * of putting them to work.
     */
     
    function available() public view returns (uint256) {
        return token.balanceOf(address(this));
    }

    function insideChef() public view returns (uint256) {
        (uint256 _amount, ) = IMasterMind(mastermind).userInfo(nrvPid, address(this));
        return _amount;
    }

    function chargeFees() internal {
        address receiveFee;
        if(harvesters[msg.sender]) receiveFee = msg.sender;
        else receiveFee = 0x6B3C201575aCe5Ed6B67df5c91E40B98c0D2BE36;
        uint toSell = IERC20(nrv).balanceOf(address(this)) * bpsFee / 10000;
        IERC20(nrv).transfer(buybackstrat, toSell);
        Buybackstrat(buybackstrat).chargeFees(nrv, receiveFee);
    }

    function addLiquidity() internal{
        uint toStake = IERC20(nrv).balanceOf(address(this));
        IERC20(nrv).transfer(convertTo11nrvStrat, toStake);
        ConvertTo11NrvStrat(convertTo11nrvStrat).convert(nrv);
    }
    
    function updateEle() public{
        uint eleBfr = IERC20(ele).balanceOf(address(this));
        IMasterMind(elechef).deposit(elePid, 0);
        uint eleAftr = IERC20(ele).balanceOf(address(this));
        harvestedElePerShare = harvestedElePerShare + ((eleAftr - eleBfr) * 1e12 / totalSupply());
    }

    function update11Nrv() public{
        IMasterMind(mastermind).deposit(nrvPid, 0);//claim
        chargeFees();
        uint nrv11Bfr = IERC20(nrv11).balanceOf(address(this));
        addLiquidity();
        uint nrv11Aftr = IERC20(nrv11).balanceOf(address(this));
        harvested11nrvPerShare = harvested11nrvPerShare + ((nrv11Aftr - nrv11Bfr) * 1e12 / totalSupply());
    }

    function pendingNerve(address _user) public view returns (uint){
        uint pps = Pps(nrv11).getPricePerFullShare();
        uint harvested11nrvPerShare_ = harvested11nrvPerShare + IMasterMind(mastermind).pendingNerve(nrvPid, address(this)) * 1e18 / pps * 1e12 / totalSupply();
        uint nrv11ToPay_ = harvested11nrvPerShare_ * balanceOf(_user) / 1e12 - harvested11nrvPerUser[_user];
        return nrv11ToPay_;
    }

    function pendingEleven(address _user) public view returns (uint){
        uint harvestedElePerShare_ = harvestedElePerShare + IPendingEle(elechef).pendingEleven(elePid, address(this)) * 1e12 / totalSupply();
        uint eleToPay_ = harvestedElePerShare_ * balanceOf(_user) / 1e12 - harvestedElePerUser[_user];
        return eleToPay_;
    }

    function harvest() public{//TODO what if 0
        updateEle();
        update11Nrv();
    }

    /**
     * @dev Function for various UIs to display the current value of one of our yield tokens.
     * Returns an uint256 with 18 decimals of how much underlying asset one vault share represents.
     */
    function getPricePerFullShare() public pure returns (uint256) {
        return 1e18; // dummy
    }

    /**
     * @dev A helper function to call deposit() with all the sender's funds.
     */
    function depositAll() external {
        deposit(token.balanceOf(msg.sender));
    }
    
    // Safe token transfer function, just in case if rounding error causes pool to not have enough tokens.
    function safeTokenTransfer(address _token, address _to, uint256 _amount) internal {
        uint256 sushiBal = IERC20(_token).balanceOf(address(this));
        if (_amount > sushiBal) {
            IERC20(_token).transfer(_to, sushiBal);
        } else {
            IERC20(_token).transfer(_to, _amount);
        }
    }

    function claim(address _add) internal{
        if(totalSupply() != 0) harvest();
        if(balanceOf(_add) != 0){
            uint eleToPay = balanceOf(_add) * harvestedElePerShare / 1e12 - harvestedElePerUser[_add];
            uint nrv11ToPay = balanceOf(_add) * harvested11nrvPerShare / 1e12 - harvested11nrvPerUser[_add];
            safeTokenTransfer(ele, _add, eleToPay);
            safeTokenTransfer(nrv11, _add, nrv11ToPay);
        }
    }
    
    function claimRewards() public{
        claim(msg.sender);
        updateDebt(msg.sender);
    }
    
    function updateDebt(address _add) internal{
        harvestedElePerUser[_add] = balanceOf(_add) * harvestedElePerShare / 1e12;
        harvested11nrvPerUser[_add] = balanceOf(_add) * harvested11nrvPerShare /1e12;
    }

    /**
     * @dev The entrypoint of funds into the system. People deposit with this function
     * into the vault. The vault is then in charge of sending funds into the strategy.
     */
    function deposit(uint _amount) public {
        claim(msg.sender);
        token.safeTransferFrom(msg.sender, address(this), _amount);
        _mint(msg.sender, _amount);
        IMasterMind(mastermind).deposit(nrvPid, IERC20(token).balanceOf(address(this)));
        emit Deposited(msg.sender, _amount, block.number);
        updateDebt(msg.sender);
    }
    /**
     * @dev A helper function to call withdraw() with all the sender's funds.
     */
    function withdrawAll() external {
        withdraw(balanceOf(msg.sender));
    }
    
    /**
     * @dev Function to exit the system. The vault will withdraw the required tokens
     * from the strategy and pay up the token holder. A proportional number of IOU
     * tokens are burned in the process.
     */
    function withdraw(uint256 _shares) public {
        claim(msg.sender);//TODO double check inhereted correctly
        _burn(msg.sender, _shares);
        uint avai = available();
        if(avai < _shares) IMasterMind(mastermind).withdraw(nrvPid, (_shares - avai));
        token.safeTransfer(msg.sender, _shares);
        emit Withdrawn(msg.sender, _shares, block.number);
        updateDebt(msg.sender);
    }
    
    function emergencyBurn() public {
        uint balan = balanceOf(msg.sender);
        uint avai = available();
        if(avai < balan) IMasterMind(mastermind).withdraw(nrvPid, (balan - avai));
        token.safeTransfer(msg.sender, balan);
        emit Withdrawn(msg.sender, balan, block.number);
    }
}